import logging
from pydantic_settings import BaseSettings
from logging.config import dictConfig
from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    model_path: str = str(BASE_DIR / "model")

    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN")

    flower_descriptions: dict = {
 "1": "Розовая примула (pink primrose)",
 "2": "Жестколистная карманная орхидея (hard-leaved pocket orchid)",
 "3": "Кентерберийские колокольчики (canterbury bells)",
 "4": "Душистый горошек (sweet pea)",
 "5": "Английская календула (english marigold)",
 "6": "Тигровая лилия (tiger lily)",
 "7": "Лунная орхидея (moon orchid)",
 "8": "Стрелиция / райская птица (bird of paradise)",
 "9": "Аконит (monkshood)",
 "10": "Мордовник шароголовый (globe thistle)",
 "11": "Львиный зев (snapdragon)",
 "12": "Мать-и-мачеха (colt's foot)",
 "13": "Протея королевская (king protea)",
 "14": "Чертополох копьевидный (spear thistle)",
 "15": "Жёлтый ирис (yellow iris)",
 "16": "Купальница (globe-flower)",
 "17": "Эхинацея пурпурная (purple coneflower)",
 "18": "Перуанская лилия / альстромерия (peruvian lily)",
 "19": "Платикодон (balloon flower)",
 "20": "Белая калла (giant white arum lily)",
 "21": "Огненная лилия (fire lily)",
 "22": "Скабиоза (pincushion flower)",
 "23": "Рябчик (fritillary)",
 "24": "Красный имбирь (red ginger)",
 "25": "Мускари (grape hyacinth)",
 "26": "Мак (corn poppy)",
 "27": "Амарант (prince of wales feathers)",
 "28": "Горечавка (stemless gentian)",
 "29": "Артишок (artichoke)",
 "30": "Гвоздика бородатая (sweet william)",
 "31": "Гвоздика (carnation)",
 "32": "Флокс (garden phlox)",
 "33": "Нигелла (love in the mist)",
 "34": "Мексиканская астра (mexican aster)",
 "35": "Синеголовник (alpine sea holly)",
 "36": "Каттлея (ruby-lipped cattleya)",
 "37": "Капский цветок (cape flower)",
 "38": "Астранция (great masterwort)",
 "39": "Сиамский тюльпан (siam tulip)",
 "40": "Морозник (lenten rose)",
 "41": "Гербера (barbeton daisy)",
 "42": "Нарцисс (daffodil)",
 "43": "Гладиолус (sword lily)",
 "44": "Пуансеттия (poinsettia)",
 "45": "Петуния Болеро (bolero deep blue)",
 "46": "Левкой (wallflower)",
 "47": "Бархатцы (marigold)",
 "48": "Лютик (buttercup)",
 "49": "Ромашка (oxeye daisy)",
 "50": "Одуванчик (common dandelion)",
 "51": "Петуния (petunia)",
 "52": "Анютины глазки (wild pansy)",
 "53": "Примула (primula)",
 "54": "Подсолнух (sunflower)",
 "55": "Пеларгония (pelargonium)",
 "56": "Георгина Бишоп (bishop of llandaff)",
 "57": "Гаура (gaura)",
 "58": "Герань (geranium)",
 "59": "Оранжевая георгина (orange dahlia)",
 "60": "Георгина (pink-yellow dahlia)",
 "61": "Каутлея (cautleya spicata)",
 "62": "Японская анемона (japanese anemone)",
 "63": "Рудбекия (black-eyed susan)",
 "64": "Серебристый куст (silverbush)",
 "65": "Калифорнийский мак (californian poppy)",
 "66": "Остеоспермум (osteospermum)",
 "67": "Крокус (spring crocus)",
 "68": "Бородатый ирис (bearded iris)",
 "69": "Ветреница (windflower)",
 "70": "Древовидный мак (tree poppy)",
 "71": "Газания (gazania)",
 "72": "Азалия (azalea)",
 "73": "Кувшинка (water lily)",
 "74": "Роза (rose)",
 "75": "Дурман (thorn apple)",
 "76": "Ипомея (morning glory)",
 "77": "Пассифлора (passion flower)",
 "78": "Лотос (lotus)",
 "79": "Трициртис (toad lily)",
 "80": "Антуриум (anthurium)",
 "81": "Плюмерия (frangipani)",
 "82": "Клематис (clematis)",
 "83": "Гибискус (hibiscus)",
 "84": "Аквилегия (columbine)",
 "85": "Адениум (desert-rose)",
 "86": "Мальва древовидная (tree mallow)",
 "87": "Магнолия (magnolia)",
 "88": "Цикламен (cyclamen)",
 "89": "Кресс водяной (watercress)",
 "90": "Канна (canna lily)",
 "91": "Гиппеаструм (hippeastrum)",
 "92": "Монарда (bee balm)",
 "93": "Тилландсия (ball moss)",
 "94": "Наперстянка (foxglove)",
 "95": "Бугенвиллея (bougainvillea)",
 "96": "Камелия (camellia)",
 "97": "Мальва (mallow)",
 "98": "Мексиканская петуния (mexican petunia)",
 "99": "Бромелия (bromelia)",
 "100": "Гайлардия (blanket flower)",
 "101": "Кампсис (trumpet creeper)",
 "102": "Лилия ежевичная (blackberry lily)"
}


    class Config:
        protected_namespaces = ('settings_',)


LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": "%(levelprefix)s %(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
    },
    "loggers": {
        "app": {
            "handlers": ["default"],
            "level": "DEBUG",  # INFO или DEBUG
            "propagate": False
        },
        "gdown": {
            "handlers": ["default"],
            "level": "WARNING"
        }
    }
}

dictConfig(LOG_CONFIG)
logger = logging.getLogger("app")

settings = Settings()
