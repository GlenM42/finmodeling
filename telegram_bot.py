import asyncio
import os

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, filters, ContextTypes

from commands_for_management import initialize_portfolio, calculate_performance, show_portfolio_as_image, plot_portfolio_performance, \
    fetch_option_data_and_show_returns
from commands_for_options import add_option_start, option_ticker_received, option_quantity_received, \
    option_purchase_price_received, option_purchase_date_received, option_final_confirmation, remove_option_start, \
    option_remove_ticker_received, option_remove_purchase_date_received, option_remove_final_confirmation
from commands_for_transactions import add_transaction_start, ticker_received, confirm_ticker, quantity_received, \
    purchase_date_received, purchase_price_received, final_confirmation, remove_transaction_start, \
    remove_ticker_received, remove_date_received, remove_confirmation

# Define states
TICKER, CONFIRM_TICKER, QUANTITY, PURCHASE_DATE, PURCHASE_PRICE, CONFIRMATION = range(6)
REMOVE_TICKER, REMOVE_DATE, REMOVE_CONFIRMATION = range(6, 9)
(OPTION_TICKER, OPTION_QUANTITY, OPTION_PURCHASE_DATE, OPTION_PURCHASE_PRICE, OPTION_CONFIRMATION) = range(5)
(OPTION_REMOVE_TICKER, OPTION_REMOVE_PURCHASE_DATE, OPTION_REMOVE_CONFIRMATION) = range(2, 5)

ADMIN_USER_IDS = [
    os.getenv('ADMIN_TELEGRAM_ID_1'),
    os.getenv('ADMIN_TELEGRAM_ID_2')
]


# Define your async start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Accessing the message object
    message = update.message

    # Building a response string that includes some details of the message
    response = (
        f"Hello, Mr. {message.from_user.full_name if message.from_user else 'N/A'}! "
        f"I would like to help you with your portfolio management."
    )

    # Sending the details back as a message
    await context.bot.send_message(chat_id=update.effective_chat.id, text=response)


# Define your async portfolio command handler
async def portfolio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id  # Get the user ID of the person sending the command

    if user_id not in ADMIN_USER_IDS:
        # If the user is not in the list of admins, send an unauthorized message
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=f"You are not authorized to view the portfolio. Contact "
                                            f"admin in case you needed to be added (your user ID is: {user_id})")
    else:
        # If the user is an admin, proceed with showing the portfolio
        portfolio_df = await asyncio.to_thread(initialize_portfolio)
        portfolio_perf = await asyncio.to_thread(calculate_performance, portfolio_df)

        # Use the modified functions to save images
        await asyncio.to_thread(show_portfolio_as_image, portfolio_perf, 'portfolio_table.png')
        await asyncio.to_thread(plot_portfolio_performance, portfolio_perf, 'portfolio_performance.png')

        # Send the images
        with open('portfolio_table.png', 'rb') as file:
            await context.bot.send_photo(chat_id=update.effective_chat.id, photo=file)
        with open('portfolio_performance.png', 'rb') as file:
            await context.bot.send_photo(chat_id=update.effective_chat.id, photo=file)

        # Delete the images after sending
        os.remove('portfolio_table.png')
        os.remove('portfolio_performance.png')


async def show_option_returns(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Fetching option data and generating returns... Please wait.")

    # Assuming fetch_option_data_and_show_returns is modified to return file paths of the generated images
    table_image_path, returns_image_path = await asyncio.to_thread(fetch_option_data_and_show_returns)

    # Send the generated images
    with open(table_image_path, 'rb') as table_image, open(returns_image_path, 'rb') as returns_image:
        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=table_image)
        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=returns_image)

    # Cleanup: Delete the images after sending
    os.remove(table_image_path)
    os.remove(returns_image_path)


async def abort_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Operation aborted. If you need help or wish to perform "
                                    "another operation, just let me know.")
    return ConversationHandler.END


def main():
    application = Application.builder().token(os.getenv('TELEGRAM_API')).build()

    add_transaction_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('add_transaction', add_transaction_start)],
        states={
            TICKER: [MessageHandler(filters.TEXT & ~filters.COMMAND, ticker_received)],
            CONFIRM_TICKER: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_ticker)],
            QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, quantity_received)],
            PURCHASE_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, purchase_date_received)],
            PURCHASE_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, purchase_price_received)],
            CONFIRMATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, final_confirmation)]
        },
        fallbacks=[
            CommandHandler('abort', abort_conversation),
        ]
    )

    remove_transaction_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('remove_transaction', remove_transaction_start)],
        states={
            REMOVE_TICKER: [MessageHandler(filters.TEXT & ~filters.COMMAND, remove_ticker_received)],
            REMOVE_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, remove_date_received)],
            REMOVE_CONFIRMATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, remove_confirmation)]
        },
        fallbacks=[CommandHandler('abort', abort_conversation)],
    )

    add_option_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('add_option', add_option_start)],
        states={
            OPTION_TICKER: [MessageHandler(filters.TEXT & ~filters.COMMAND, option_ticker_received)],
            OPTION_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, option_quantity_received)],
            OPTION_PURCHASE_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, option_purchase_price_received)],
            OPTION_PURCHASE_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, option_purchase_date_received)],
            OPTION_CONFIRMATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, option_final_confirmation)]
        },
        fallbacks=[CommandHandler('abort', abort_conversation)]
    )

    remove_option_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('remove_option', remove_option_start)],
        states={
            OPTION_REMOVE_TICKER: [MessageHandler(filters.TEXT & ~filters.COMMAND, option_remove_ticker_received)],
            OPTION_REMOVE_PURCHASE_DATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, option_remove_purchase_date_received)],
            OPTION_REMOVE_CONFIRMATION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, option_remove_final_confirmation)]
        },
        fallbacks=[CommandHandler('abort', abort_conversation)]
    )

    # Add handlers to the application
    application.add_handler(add_transaction_conv_handler)
    application.add_handler(remove_transaction_conv_handler)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("portfolio", portfolio))
    application.add_handler(CommandHandler("show_option_returns", show_option_returns))
    application.add_handler(add_option_conv_handler)
    application.add_handler(remove_option_conv_handler)

    # Run the bot until the user presses Ctrl-C
    application.run_polling()


if __name__ == '__main__':
    main()
