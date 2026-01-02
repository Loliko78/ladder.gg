"""
Модуль для анализа скриншотов Majestic RP
Позволяет распознавать количество побед и проигрышей из экрана
"""

import pytesseract
from PIL import ImageGrab, Image
import re
import os
from datetime import datetime

class MajesticScreenAnalyzer:
    """Анализатор скриншотов из Majestic RP"""
    
    # Типичные позиции элементов на экране (для разных разрешений)
    SCREEN_REGIONS = {
        '1920x1080': {
            'right_quarter': (1440, 0, 1920, 1080),  # Правый 1/4 экрана
            'stats_region': (1500, 300, 1920, 700),   # Область со статистикой
        },
        '1600x900': {
            'right_quarter': (1200, 0, 1600, 900),
            'stats_region': (1250, 250, 1600, 650),
        },
        '1280x720': {
            'right_quarter': (960, 0, 1280, 720),
            'stats_region': (1000, 200, 1280, 550),
        }
    }
    
    def __init__(self):
        """Инициализация анализатора"""
        self.last_screenshot = None
        self.last_analysis = None
        
    def capture_right_quarter(self):
        """Захватывает правый 1/4 экрана"""
        try:
            # Получаем размер экрана
            screenshot = ImageGrab.grab()
            width, height = screenshot.size
            resolution = f"{width}x{height}"
            
            # Выбираем нужный регион в зависимости от разрешения
            if resolution in self.SCREEN_REGIONS:
                region = self.SCREEN_REGIONS[resolution]['right_quarter']
            else:
                # Для неизвестного разрешения берем правый 1/4
                region = (int(width * 0.75), 0, width, height)
            
            # Захватываем нужный регион
            right_quarter = screenshot.crop(region)
            self.last_screenshot = right_quarter
            
            return right_quarter
            
        except Exception as e:
            print(f"Ошибка при захвате скриншота: {e}")
            return None
    
    def extract_text(self, image):
        """Извлекает текст из изображения используя OCR"""
        try:
            if image is None:
                return ""
            
            # Используем Tesseract для распознавания текста
            text = pytesseract.image_to_string(image, lang='rus+eng')
            return text
            
        except Exception as e:
            print(f"Ошибка при распознавании текста: {e}")
            return ""
    
    def parse_match_result(self, text):
        """
        Парсит результат матча из текста
        Ищет паттерны типа:
        - "Победа" / "Поражение"
        - "+50 GGP" / "-25 GGP"
        - "Wins: 123 Losses: 45"
        """
        result = {
            'status': None,
            'ggp_change': 0,
            'wins': None,
            'losses': None,
            'confidence': 0.0
        }
        
        # Ищем слово "Победа" или "Поражение"
        if re.search(r'побед|win', text.lower()):
            result['status'] = 'win'
            result['confidence'] += 0.3
        elif re.search(r'поражени|loss', text.lower()):
            result['status'] = 'loss'
            result['confidence'] += 0.3
        
        # Ищем изменение GGP
        ggp_match = re.search(r'([+-]?\d+)\s*GGP', text)
        if ggp_match:
            result['ggp_change'] = int(ggp_match.group(1))
            result['confidence'] += 0.2
        
        # Ищем статистику побед/поражений
        wins_match = re.search(r'(?:wins?|побед)[\s:]*(\d+)', text, re.IGNORECASE)
        if wins_match:
            result['wins'] = int(wins_match.group(1))
            result['confidence'] += 0.25
        
        losses_match = re.search(r'(?:losses?|поражени)[\s:]*(\d+)', text, re.IGNORECASE)
        if losses_match:
            result['losses'] = int(losses_match.group(1))
            result['confidence'] += 0.25
        
        return result
    
    def analyze_screenshot(self):
        """
        Основной метод анализа скриншота
        Возвращает словарь с результатами матча
        """
        # Захватываем скриншот
        image = self.capture_right_quarter()
        if image is None:
            return {
                'success': False,
                'error': 'Не удалось захватить скриншот'
            }
        
        # Сохраняем скриншот для отладки (опционально)
        # image.save(f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        
        # Извлекаем текст
        text = self.extract_text(image)
        
        # Парсим результат
        result = self.parse_match_result(text)
        result['raw_text'] = text
        result['success'] = True
        result['timestamp'] = datetime.now().isoformat()
        
        self.last_analysis = result
        
        return result
    
    def validate_result(self, result):
        """Проверяет надежность результата анализа"""
        return {
            'is_valid': result.get('confidence', 0) >= 0.5,
            'confidence': result.get('confidence', 0),
            'status': result.get('status'),
            'needs_confirmation': result.get('confidence', 0) < 0.7
        }
    
    def save_screenshot(self, filepath):
        """Сохраняет последний захватанный скриншот"""
        if self.last_screenshot:
            self.last_screenshot.save(filepath)
            return True
        return False


# Пример использования
if __name__ == '__main__':
    analyzer = MajesticScreenAnalyzer()
    
    # Захватываем и анализируем скриншот
    result = analyzer.analyze_screenshot()
    
    print("Результаты анализа:")
    print(f"Статус: {result.get('status')}")
    print(f"Изменение GGP: {result.get('ggp_change')}")
    print(f"Победы: {result.get('wins')}")
    print(f"Поражения: {result.get('losses')}")
    print(f"Уверенность: {result.get('confidence'):.0%}")
    
    # Проверяем валидность
    validation = analyzer.validate_result(result)
    print(f"\nВалидация:")
    print(f"Валидно: {validation['is_valid']}")
    print(f"Требует подтверждения: {validation['needs_confirmation']}")
