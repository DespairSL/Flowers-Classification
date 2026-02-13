import torch
from transformers import AutoModelForImageClassification, AutoImageProcessor
from PIL import Image
import os
import logging
from .config import settings


class FlowerClassifier:
    def __init__(self):
        self.logger = logging.getLogger("app.services")
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.logger.info(f"Инициализация классификатора. Устройство: {self.device}")
        self.model = None
        self.processor = None
        self.load_model()

    def load_model(self):
        """Загрузка модели и процессора из локальной директории"""
        model_dir = settings.model_path
        self.logger.info(f"Начало загрузки модели из локальной директории: {model_dir}")

        try:
            # Проверяем, что все обязательные файлы существуют в папке model
            required_files = ["config.json", "model.safetensors", "preprocessor_config.json"]
            for file in required_files:
                file_path = os.path.join(model_dir, file)
                if not os.path.exists(file_path):
                    error_msg = f"Файл {file} не найден в {model_dir}!"
                    self.logger.error(error_msg)
                    raise FileNotFoundError(error_msg)

            # Загружаем модель и процессор из локальной директории
            self.logger.info("Загрузка модели в память...")
            self.model = AutoModelForImageClassification.from_pretrained(
                model_dir,
                local_files_only=True,
                use_safetensors=True
            ).to(self.device)

            self.processor = AutoImageProcessor.from_pretrained(
                model_dir,
                local_files_only=True
            )
            self.logger.info("Модель успешно загружена!")

        except Exception as e:
            self.logger.error(f"Критическая ошибка при загрузке модели: {str(e)}")
            raise RuntimeError(f"Ошибка загрузки модели: {e}")

    def predict(self, image_path: str):
        """Предсказание классов грибов по изображению"""
        self.logger.info(f"Начало обработки изображения: {image_path}")
        try:
            image = Image.open(image_path)
            self.logger.debug("Изображение успешно открыто")

            if image.mode != "RGB":
                self.logger.debug("Конвертация изображения в RGB")
                image = image.convert("RGB")

            self.logger.debug("Подготовка входных данных для модели")
            inputs = self.processor(images=image, return_tensors="pt").to(self.device)

            self.logger.debug("Выполнение предсказания")
            with torch.no_grad():
                outputs = self.model(**inputs)

            probs = torch.nn.functional.softmax(outputs.logits, dim=-1)[0]
            top5_probs, top5_indices = torch.topk(probs, 5)

            results = []
            for prob, idx in zip(top5_probs, top5_indices):
                class_name = self.model.config.id2label[idx.item()]
                results.append({
                    "class_name": class_name,
                    "confidence": float(prob) * 100
                })

            self.logger.info("Предсказание успешно завершено")
            return results

        except FileNotFoundError:
            error_msg = f"Файл {image_path} не найден!"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        except Exception as e:
            self.logger.error(f"Ошибка при выполнении предсказания: {str(e)}")
            raise
