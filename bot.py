# bot.py
import logging
import random
import numpy as np
import os
from dotenv import load_dotenv

load_dotenv()

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

from quiz_data import QUIZ_QUESTIONS


# Enable logging to see debug output (useful for troubleshooting)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Constants
STATE_QUIZ_ACTIVE = "quiz_active"
QUESTIONS_PER_QUIZ = 5  # Add this constant to control how many questions per quiz

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /start command handler: initializes user data and sends the first question.
    """
    # Initialize quiz state
    context.user_data["current_question_index"] = 0
    context.user_data["correct_answers"] = np.array((0,0,0,0))
    context.user_data[STATE_QUIZ_ACTIVE] = True
    
    # Create a randomized subset of questions for this session
    # context.user_data["randomized_questions"] = random.sample(QUIZ_QUESTIONS, QUESTIONS_PER_QUIZ)
    
    # Create a deterministic subset of questions for this session
    context.user_data["randomized_questions"] = QUIZ_QUESTIONS[:QUESTIONS_PER_QUIZ]

    await send_question(update, context)

async def send_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Sends the current question as inline keyboard buttons.
    """
    question_index = context.user_data["current_question_index"]
    question_data = context.user_data["randomized_questions"][question_index]

    # Create a list of tuples containing (option text, original index)
    options_with_indices = list(enumerate(options := question_data["options"]))
    # Shuffle the options while keeping track of the correct answer
    random.shuffle(options_with_indices)

    # Create the full question text with options
    question_text = f"Question {question_index + 1}/{QUESTIONS_PER_QUIZ}:\n\n{question_data['question']}\n\n"
    
    # Add options to question text
    for idx, (_, option_dict) in enumerate(options_with_indices):
        # option_letter = chr(65 + idx)  # Convert 0,1,2,3 to A,B,C,D
        option_letter = option_dict['bulletpoint']
        question_text += f'{option_letter}. {option_dict["text"]}\n'

    # Create simple A,B,C,D keyboard
    keyboard = []
    for idx, (original_index, option_dict) in enumerate(options_with_indices):
        stat = option_dict["stat"]
        option_letter = option_dict['bulletpoint']
        keyboard.append([
            InlineKeyboardButton(
                text=option_letter,
                callback_data=f"{question_index}|{idx}|{stat}|{original_index}"
            )
        ])

    reply_markup = InlineKeyboardMarkup(keyboard)

      # Acknowledge the callback query
    # If triggered by /start, reply to the message;
    # if triggered by callback, use the callback query's message instead
    if update.message:
        await update.message.reply_text(text=question_text, reply_markup=reply_markup)
    else:
        query = update.callback_query
        # If it's a callback, post the next question
        await context.bot.send_message(chat_id=query.message.chat_id, text=question_text, reply_markup=reply_markup)
        # If it's a callback, edit the message to show the next question
        # await query.edit_message_text(text=question_text, reply_markup=reply_markup)
    
    
    # context.bot.send_message(chat_id=query.message.chat_id, text="You selected Option 1!")
    

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Processes the user's answer from the inline keyboard callback.
    """
    if not context.user_data.get(STATE_QUIZ_ACTIVE, False):
        await update.callback_query.answer("The quiz is not active. Use /start to begin.")
        return

    
    
    # Parse callback_data
    callback_data = update.callback_query.data
    question_index_str, _, stat_str, original_option_index_str = callback_data.split("|")
    question_index = int(question_index_str)
    selected_original_index = int(original_option_index_str)
    stat = [int(i) for i in stat_str.strip("()").split(",")]

    # Check if the answer is correct
    question_data = context.user_data["randomized_questions"][question_index]
    bulletpoint = question_data["options"][selected_original_index]["bulletpoint"]
    # bulletpoint = question_data['question']['bulletpoint']
    context.user_data["correct_answers"] += np.array(stat)
    feedback = "+"+bulletpoint

    # Show feedback message
    await update.callback_query.answer(feedback, show_alert=False)

    # Go to next question
    context.user_data["current_question_index"] += 1
    question_index = context.user_data["current_question_index"]

    # If we're at the end of the quiz, show results
    if question_index >= QUESTIONS_PER_QUIZ+1:
        await show_result(update, context)
        return

    # Otherwise, show the next question
    await send_question(update, context)

async def show_result(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Displays the final quiz result.
    """
    correct_answers = context.user_data["correct_answers"]
    total_questions = QUESTIONS_PER_QUIZ  # Update this to use the constant

    score_text = str(correct_answers)
    
    # score_text = f"You got {correct_answers} out of {total_questions} questions correct!"
    context.user_data[STATE_QUIZ_ACTIVE] = False  # Mark quiz as finished

    # Edit the last message with the final score
    await update.callback_query.edit_message_text(text=score_text)

def main():
    """Start the bot."""
    # Replace 'YOUR_BOT_TOKEN' with your actual bot token
    token = os.getenv('TOKEN')
    application = ApplicationBuilder().token(token).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_answer))

    # Run the bot until the user stops it with Ctrl-C
    application.run_polling()

if __name__ == "__main__":
    main()
