#!/usr/bin/env python3
"""
টেলিগ্রাম বট - মেইল চেকার এবং IBAN জেনারেটর
"""

import os
import re
import asyncio
import random
import logging
from datetime import datetime
from dotenv import load_dotenv
import requests
from imap_tools import MailBox, AND
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ContextTypes, filters
)

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")

# কান্ট্রি কোড ম্যাপিং
COUNTRY_MAP = {
    "জার্মানি": "DE", "ফ্রান্স": "FR", "যুক্তরাজ্য": "GB",
    "ইতালি": "IT", "স্পেন": "ES", "নেদারল্যান্ডস": "NL",
    "বেলজিয়াম": "BE", "অস্ট্রিয়া": "AT", "সুইজারল্যান্ড": "CH",
    "পোল্যান্ড": "PL", "সুইডেন": "SE", "নরওয়ে": "NO",
    "ডেনমার্ক": "DK", "ফিনল্যান্ড": "FI", "আয়ারল্যান্ড": "IE",
    "পর্তুগাল": "PT", "গ্রীস": "GR", "চেক রিপাবলিক": "CZ",
    "হাঙ্গেরি": "HU", "বুলগেরিয়া": "BG", "ক্রোয়েশিয়া": "HR",
}

IBAN_FORMATS = {
    "DE": {"length": 22, "bank_len": 8, "account_len": 10, "name": "Germany"},
    "FR": {"length": 27, "bank_len": 10, "account_len": 11, "name": "France"},
    "GB": {"length": 22, "bank_len": 6, "account_len": 8, "name": "UK"},
    "IT": {"length": 27, "bank_len": 11, "account_len": 12, "name": "Italy"},
    "ES": {"length": 24, "bank_len": 8, "account_len": 10, "name": "Spain"},
    "NL": {"length": 18, "bank_len": 4, "account_len": 10, "name": "Netherlands"},
}

async def generate_iban_api(country_code: str):
    try:
        url = f"https://randomiban.co/?country={country_code}&format=json"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {
                "iban": data.get('iban', ''),
                "bank_name": data.get('bank', {}).get('name', 'Unknown Bank'),
                "bic": data.get('bic', ''),
                "bank_address": data.get('bank', {}).get('address', 'N/A'),
                "country_code": country_code
            }
        return None
    except Exception as e:
        logger.error(f"API Error: {e}")
        return None

async def generate_iban_local(country_code: str):
    if country_code not in IBAN_FORMATS:
        return None
    fmt = IBAN_FORMATS[country_code]
    bank_code = ''.join([str(random.randint(0, 9)) for _ in range(fmt["bank_len"])])
    account_num = ''.join([str(random.randint(0, 9)) for _ in range(fmt["account_len"])])
    bban = bank_code + account_num
    iban = f"{country_code}88{bban}"
    return {
        "iban": iban,
        "bank_name": f"Random Bank of {fmt['name']}",
        "bic": f"{country_code}XXYYZZZ",
        "bank_address": f"Financial District, {fmt['name']}",
        "country_code": country_code
    }

async def generate_iban(country_code: str):
    result = await generate_iban_api(country_code)
    if result and result.get('iban'):
        return result
    return await generate_iban_local(country_code)

def get_country_code(country_name: str):
    if country_name in COUNTRY_MAP:
        return COUNTRY_MAP[country_name]
    for name, code in COUNTRY_MAP.items():
        if country_name.lower() in name.lower() or name.lower() in country_name.lower():
            return code
    return None

async def check_emails(limit=5):
    try:
        with MailBox('imap.gmail.com').login(MAIL_USERNAME, MAIL_PASSWORD, 'INBOX') as mailbox:
            emails = []
            for msg in mailbox.fetch(AND(all=True), limit=limit, reverse=True):
                emails.append({
                    'subject': msg.subject,
                    'from': msg.from_,
                    'date': msg.date.strftime("%Y-%m-%d %H:%M:%S"),
                    'body': msg.text[:200] if msg.text else '',
                    'uid': msg.uid
                })
            return emails
    except Exception as e:
        logger.error(f"Mail check error: {e}")
        return None

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 **Telegram IBAN Bot**\n\n"
        "📧 `/checkmail` - ইমেইল চেক করুন\n"
        "🏦 `/iban দেশের_নাম` - IBAN জেনারেট করুন\n"
        "ℹ️ `/help` - সাহায্য\n\n"
        "উদাহরণ: `/iban জার্মানি`",
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 **কমান্ড লিস্ট**\n\n"
        "`/iban জার্মানি` - জার্মান IBAN\n"
        "`/iban ফ্রান্স` - ফ্রেঞ্চ IBAN\n"
        "`/iban যুক্তরাজ্য` - UK IBAN\n"
        "`/checkmail` - ইমেইল চেক\n\n"
        f"সাপোর্টেড দেশ: {', '.join(list(COUNTRY_MAP.keys())[:10])}",
        parse_mode='Markdown'
    )

async def iban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ ব্যবহার: `/iban জার্মানি`", parse_mode='Markdown')
        return
    
    country_input = ' '.join(context.args).strip()
    country_code = get_country_code(country_input)
    
    if not country_code:
        await update.message.reply_text(f"❌ '{country_input}' সাপোর্ট করে না")
        return
    
    msg = await update.message.reply_text(f"🏦 {country_input} এর জন্য IBAN তৈরি হচ্ছে...")
    
    iban_data = await generate_iban(country_code)
    
    if not iban_data:
        await msg.edit_text("❌ ব্যর্থ হয়েছে")
        return
    
    iban = iban_data['iban']
    formatted = ' '.join([iban[i:i+4] for i in range(0, len(iban), 4)])
    
    text = (
        f"🏦 **{country_input}**\n\n"
        f"💳 `{formatted}`\n"
        f"🏛️ {iban_data['bank_name']}\n"
        f"🔑 `{iban_data['bic']}`\n\n"
        f"⚠️ টেস্টিং এর জন্য"
    )
    
    keyboard = [[InlineKeyboardButton("📋 কপি", callback_data=f"copy_{iban}")]]
    await msg.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def checkmail_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text("⏳ ইমেইল চেক হচ্ছে...")
    emails = await check_emails(5)
    
    if emails is None:
        await msg.edit_text("❌ সংযোগ ব্যর্থ")
        return
    
    if not emails:
        await msg.edit_text("📭 কোন ইমেইল নেই")
        return
    
    reply = f"📧 **সর্বশেষ {len(emails)}টি ইমেইল**\n\n"
    for i, email in enumerate(emails[:3], 1):
        reply += f"**{i}. {email['subject'][:40]}**\n   From: {email['from']}\n\n"
    
    await msg.edit_text(reply, parse_mode='Markdown')

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("copy_"):
        iban = query.data.replace("copy_", "")
        await query.edit_message_text(f"✅ কপি করুন:\n`{iban}`", parse_mode='Markdown')
        await asyncio.sleep(3)
        await query.delete_message()

def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN পাওয়া যায়নি")
        return
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("iban", iban_command))
    app.add_handler(CommandHandler("checkmail", checkmail_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    print("✅ বট চালু হয়েছে!")
    app.run_polling()

if __name__ == "__main__":
    main()
