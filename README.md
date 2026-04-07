# 🤖 fake IBAN Generator Bot

একটি টেলিগ্রাম বট যা IBAN জেনারেট করে এবং ইমেইল চেক করতে পারে।

## 📋 কমান্ড সমূহ

| কমান্ড | কাজ |
|--------|-----|
| `/start` | বট চালু করুন |
| `/help` | সাহায্য দেখুন |
| `/iban জার্মানি` | জার্মান IBAN জেনারেট |
| `/iban ফ্রান্স` | ফ্রেঞ্চ IBAN জেনারেট |
| `/checkmail` | ইমেইল চেক করুন |

## 🚀 ইনস্টলেশন

```bash
git clone https://github.com/your-username/telegram-iban-bot.git
cd telegram-iban-bot
pip install -r requirements.txt
cp .env.example .env
# .env ফাইল এডিট করে টোকেন দিন
python bot.py
