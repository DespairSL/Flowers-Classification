# Flowers-Classification

---
### Модель **-**

Использовалось в проекте:

* `"microsoft/resnet-50"`
* Размер входа: -
* Преобучена на -
---
### Данные
* **Датасет на Kaggle**: [OxFord 102 Flower Dataset](https://www.kaggle.com/datasets/yousefmohamed20/oxford-102-flower-dataset)
* **Объем датасета**: Около 8200 изображений различных цветков
* **Структура**: Все изображения цветков распределены по папкам, которые по сути являются их классами.

Датасет был загружен и преобразован в формат HuggingFace Datasets

Примененные Аугментации:

* `RandomResizedCrop`, `ColorJitter`, `GaussianBlur`, `RandomHorizontalFlip` для увеличения разнообразия обучающих примеров
* Изображения нормализованы под стандарты ViT (`mean`, `std`)

Разбиение:

* Датасет заранее разбит на Train | Validation | Test = % | % | %
* Для борьбы с дисбалансом классов использован `WeightedRandomSampler`

---

### Обучение

* Использован `Trainer` из HuggingFace с:

  * `EarlyStoppingCallback` (остановка при отсутствии улучшения)
  * `CustomTrainer` с переопределением `get_train_dataloader()` для поддержки `sampler`
* Параметры:

  * Эпохи: 15
  * Batch size: 32 (train), 8 (eval)
  * Learning rate: 5e-5, weight decay: 0.02
  * Модель сохраняется при наилучшем `eval_loss`

---
