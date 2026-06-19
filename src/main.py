import logging

from telegram.ext import Application

from src.bot import register_handlers
from src.config import load_config


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    config = load_config()
    application = Application.builder().token(config.bot_token).build()
    register_handlers(application, config)

    logger.info("Starting GroupFactory client bot")
    application.run_polling(
        allowed_updates=["message"],
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
