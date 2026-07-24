import html
from telegram import Update
from telegram.ext import ContextTypes
from gamestate import AUCTIONS, AuctionState
from utils import is_owner, user_mention

async def add_cap_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    if chat_id not in AUCTIONS:
        AUCTIONS[chat_id] = AuctionState(auction_id=str(chat_id), host_id=user_id)
        
    auc = AUCTIONS[chat_id]
    if not is_owner(user_id) and auc.host_id != user_id:
        await update.message.reply_text("⚠️ Only the Auction Host can add captains.")
        return

    if not context.args or len(context.args) < 2:
        await update.message.reply_text("Usage: `/add_cap <user_id> <Team_Name>`", parse_mode="Markdown")
        return

    cap_id = int(context.args[0])
    team_name = " ".join(context.args[1:])
    auc.captains[cap_id] = team_name
    auc.purses[cap_id] = 100.0  # Default purse 100 Cr
    await update.message.reply_text(f"✅ Added Captain <code>{cap_id}</code> for team <b>{html.escape(team_name)}</b> with purse 100 Cr.", parse_mode="HTML")

async def start_auction_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    auc = AUCTIONS.get(chat_id)
    if not auc:
        await update.message.reply_text("⚠️ No active auction set up. Use `/add_cap` first.")
        return
    await update.message.reply_text("🎪 <b>IPL Player Auction is now LIVE!</b>\nCaptains get ready with your purses!", parse_mode="HTML")
  
