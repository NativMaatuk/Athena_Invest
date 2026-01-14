import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio

# ייבוא הסוכנים הקיימים שלך
from agents import ClassicAnalyzer, DiscordNotifier
from agents.ticker_info_agent import TickerInfoAgent

# טעינת משתני סביבה
load_dotenv()

# הגדרות
TOKEN = os.getenv('DISCORD_BOT_TOKEN')
# אם תרצה שהבוט יגיב רק בערוץ ספציפי, הגדר את ה-ID שלו ב-.env
# אם לא מוגדר, הוא יגיב בכל ערוץ שיש לו גישה אליו
TARGET_CHANNEL_ID = os.getenv('DISCORD_CHANNEL_ID') 

# הגדרת הרשאות (Intents) - חובה כדי לקרוא הודעות
intents = discord.Intents.default()
intents.message_content = True 

# יצירת הבוט
bot = commands.Bot(command_prefix='!', intents=intents)

# אתחול הסוכנים
print("🔄 Initializing agents...")
analyzer = ClassicAnalyzer()
ticker_info_agent = TickerInfoAgent()
# אנו משתמשים ב-DiscordNotifier רק עבור יכולות העיצוב שלו (Formatter)
# אין צורך ב-webhook url כי הבוט שולח ישירות
formatter = DiscordNotifier(webhook_url=None)

@bot.event
async def on_ready():
    """פונקציה שרצה כשהבוט מתחבר בהצלחה"""
    print(f'✅ Bot is online! Logged in as {bot.user}')
    if TARGET_CHANNEL_ID:
        print(f'🎯 Listening restricted to channel ID: {TARGET_CHANNEL_ID}')
    else:
        print('📢 Listening on all accessible channels.')
    
    # בדיקת זמן ריצה מוגבל (עבור GitHub Actions)
    run_duration = os.getenv('RUN_DURATION_HOURS')
    if run_duration:
        try:
            hours = float(run_duration)
            print(f"⏱️ Bot will shutdown automatically after {hours} hours.")
            await asyncio.sleep(hours * 3600)
            print("🛑 Time limit reached. Shutting down...")
            await bot.close()
        except ValueError:
            print("⚠️ Invalid RUN_DURATION_HOURS value. Running indefinitely.")


@bot.event
async def on_message(message):
    """פונקציה שרצה על כל הודעה שנשלחת"""
    
    # 1. התעלם מהודעות של הבוט עצמו
    if message.author == bot.user:
        return

    # 2. אם מוגדר ערוץ ספציפי, התעלם מהודעות בערוצים אחרים
    if TARGET_CHANNEL_ID and str(message.channel.id) != str(TARGET_CHANNEL_ID):
        return

    # 3. ניקוי הטקסט וביצוע בדיקות בסיסיות
    content = message.content.strip().upper()
    
    # בדיקה שזה נראה כמו טיקר (מילה אחת, אורך סביר, מכיל רק אותיות/מספרים/נקודה/מקף)
    # אנחנו מסננים הודעות צ'אט רגילות כדי שהבוט לא ינסה לנתח את "בוקר טוב"
    if ' ' in content or len(content) > 6 or len(content) < 2:
        return
        
    # סינון תווים מיוחדים (למשל אם מישהו כתב !NVDA נוריד את ה-!)
    ticker = ''.join(c for c in content if c.isalnum() or c in ['-', '.'])
    
    if not ticker:
        return

    print(f"📩 Request received for ticker: {ticker}")

    # 4. שליחת הודעת "מעבד..."
    status_msg = await message.channel.send(f"⏳ מנתח את **{ticker}**... אנא המתן.")

    try:
        # הרצת הניתוח בתהליך נפרד (Thread) כדי לא לתקוע את הבוט
        # הפעולות analyze ו-get_ticker_info הן "חוסמות" (פונות לרשת באופן סינכרוני)
        loop = asyncio.get_event_loop()
        
        # שלב א': שליפת נתונים וחישוב
        # מריצים את analyzer.analyze ב-Executor
        df, days_until_earnings, next_earnings_date = await loop.run_in_executor(
            None, analyzer.analyze, ticker
        )
        
        # שלב ב': ביצוע הניתוח הלוגי
        analysis = analyzer.analyze_classic(df, days_until_earnings, next_earnings_date)
        analysis['ticker'] = ticker
        
        # שלב ג': שליפת מידע על החברה (סקטור, תיאור וכו')
        info = await loop.run_in_executor(
            None, ticker_info_agent.get_ticker_info, ticker
        )
        
        # שלב ד': פירמוט הטקסט (אותו פורמט כמו ב-Main הקלאסי)
        output_text = analyzer.format_output(ticker, analysis)
        
        # שלב ה': יצירת ה-Embed (הכרטיסייה המעוצבת)
        # אנו משתמשים בפונקציה הפנימית של ה-Notifier הקיים שלך
        embed_data = formatter._create_analysis_embed(
            ticker=ticker,
            content=output_text,
            is_positive=analysis['is_positive'],
            sector=info.get('sector'),
            industry=info.get('industry'),
            summary=info.get('summary'),
            market_cap=info.get('market_cap'),
            earnings_info=None # הפורמטר כבר יחלץ את המידע מתוך הטקסט
        )
        
        # המרה לאובייקט של ספריית discord.py
        embed = discord.Embed.from_dict(embed_data)
        
        # שליחת התוצאה ומחיקת הודעת ההמתנה
        await message.channel.send(embed=embed)
        await status_msg.delete()
        print(f"✅ Analysis for {ticker} sent successfully.")

    except ValueError as ve:
        # שגיאות "צפויות" כמו טיקר לא קיים
        error_msg = f"❌ לא נמצא מידע על הטיקר **{ticker}**. ודא שהכתיב נכון."
        await status_msg.edit(content=error_msg)
        print(f"⚠️ Validation error: {ve}")

    except Exception as e:
        # שגיאות בלתי צפויות
        error_msg = f"❌ שגיאה בניתוח **{ticker}**: אירעה תקלה פנימית."
        await status_msg.edit(content=error_msg)
        print(f"❌ Error analyzing {ticker}: {str(e)}")

# הרצת הבוט
if __name__ == "__main__":
    if not TOKEN:
        print("❌ Error: DISCORD_BOT_TOKEN not found in environment variables.")
    else:
        print("🚀 Starting bot...")
        bot.run(TOKEN)
