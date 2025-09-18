#!/usr/bin/env python3
"""
models/content.py - Повна система управління контентом презентації
Підтримує збереження тексту, зображень, символів та оброблених версій фолій
Dynamic Messe Stand V4 - Bertrandt
"""

import os
import json
import yaml
import shutil
import base64
import uuid
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from core.logger import logger

# =====================================================================
# КОНСТАНТИ ТА НАЛАШТУВАННЯ
# =====================================================================

SUPPORTED_IMAGE_FORMATS = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg']
SUPPORTED_FONT_FAMILIES = ['Arial', 'Helvetica', 'Times New Roman', 'Calibri', 'Roboto']
DEFAULT_SLIDE_WIDTH = 1920
DEFAULT_SLIDE_HEIGHT = 1080

@dataclass
class ElementStyle:
    """Стилі елементу"""
    color: str = '#000000'
    background_color: str = 'transparent'
    border_color: str = 'transparent'
    border_width: int = 0
    opacity: float = 1.0
    rotation: float = 0.0
    shadow: bool = False
    shadow_color: str = '#000000'
    shadow_blur: int = 5
    shadow_offset_x: int = 2
    shadow_offset_y: int = 2


# =====================================================================
# БАЗОВІ КЛАСИ ЕЛЕМЕНТІВ
# =====================================================================

class ContentElement:
    """Базовий клас для всіх елементів контенту"""
    
    def __init__(self, element_id=None, element_type="text", x=0, y=0, width=100, height=50):
        self.id = element_id or str(uuid.uuid4())
        self.type = element_type
        self.x = float(x)
        self.y = float(y) 
        self.width = float(width)
        self.height = float(height)
        self.z_index = 0
        self.visible = True
        self.locked = False
        self.created_at = datetime.now()
        self.modified_at = datetime.now()
        
        # Стилі
        self.style = ElementStyle()
        
        # Анімація
        self.animation = {
            'entrance': 'none',
            'exit': 'none',
            'duration': 1000,
            'delay': 0
        }
    
    def update_position(self, x: float, y: float) -> None:
        """Оновити позицію елементу"""
        self.x = float(x)
        self.y = float(y)
        self.modified_at = datetime.now()
    
    def update_size(self, width: float, height: float) -> None:
        """Оновити розмір елементу"""
        self.width = float(width)
        self.height = float(height)
        self.modified_at = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Базове збереження в словник"""
        return {
            'id': self.id,
            'type': self.type,
            'x': self.x,
            'y': self.y,
            'width': self.width,
            'height': self.height,
            'z_index': self.z_index,
            'visible': self.visible,
            'locked': self.locked,
            'created_at': self.created_at.isoformat(),
            'modified_at': self.modified_at.isoformat(),
            'style': {
                'color': self.style.color,
                'background_color': self.style.background_color,
                'border_color': self.style.border_color,
                'border_width': self.style.border_width,
                'opacity': self.style.opacity,
                'rotation': self.style.rotation,
                'shadow': self.style.shadow,
                'shadow_color': self.style.shadow_color,
                'shadow_blur': self.style.shadow_blur,
                'shadow_offset_x': self.style.shadow_offset_x,
                'shadow_offset_y': self.style.shadow_offset_y
            },
            'animation': self.animation
        }
    
    @classmethod
    def from_base_dict(cls, data: Dict[str, Any]) -> 'ContentElement':
        """Базове відновлення зі словника"""
        element = cls()
        element.id = data.get('id', str(uuid.uuid4()))
        element.type = data.get('type', 'text')
        element.x = float(data.get('x', 0))
        element.y = float(data.get('y', 0))
        element.width = float(data.get('width', 100))
        element.height = float(data.get('height', 50))
        element.z_index = data.get('z_index', 0)
        element.visible = data.get('visible', True)
        element.locked = data.get('locked', False)
        
        # Відновлення часу
        try:
            element.created_at = datetime.fromisoformat(data.get('created_at', datetime.now().isoformat()))
            element.modified_at = datetime.fromisoformat(data.get('modified_at', datetime.now().isoformat()))
        except:
            element.created_at = element.modified_at = datetime.now()
        
        # Відновлення стилів
        style_data = data.get('style', {})
        element.style = ElementStyle(
            color=style_data.get('color', '#000000'),
            background_color=style_data.get('background_color', 'transparent'),
            border_color=style_data.get('border_color', 'transparent'),
            border_width=style_data.get('border_width', 0),
            opacity=style_data.get('opacity', 1.0),
            rotation=style_data.get('rotation', 0.0),
            shadow=style_data.get('shadow', False),
            shadow_color=style_data.get('shadow_color', '#000000'),
            shadow_blur=style_data.get('shadow_blur', 5),
            shadow_offset_x=style_data.get('shadow_offset_x', 2),
            shadow_offset_y=style_data.get('shadow_offset_y', 2)
        )
        
        # Відновлення анімації
        element.animation = data.get('animation', {
            'entrance': 'none', 'exit': 'none', 'duration': 1000, 'delay': 0
        })
        
        return element


class TextElement(ContentElement):
    """Текстовий елемент"""
    
    def __init__(self, text="", font_family="Arial", font_size=16, **kwargs):
        super().__init__(element_type="text", **kwargs)
        self.text = str(text)
        self.font_family = font_family
        self.font_size = int(font_size)
        self.font_weight = "normal"  # normal, bold, lighter, bolder
        self.font_style = "normal"   # normal, italic, oblique
        self.text_align = "left"     # left, center, right, justify
        self.text_decoration = "none" # none, underline, line-through, overline
        self.line_height = 1.2
        self.letter_spacing = 0
        self.word_spacing = 0
        self.max_lines = None
        self.text_transform = "none"  # none, uppercase, lowercase, capitalize
        self.vertical_align = "top"   # top, middle, bottom
        self.white_space = "normal"   # normal, nowrap, pre, pre-wrap
        
        # Багаторядковий текст
        self.word_wrap = True
        self.text_overflow = "ellipsis"  # ellipsis, clip
    
    def get_formatted_text(self) -> str:
        """Отримати форматований текст"""
        text = self.text
        
        if self.text_transform == "uppercase":
            text = text.upper()
        elif self.text_transform == "lowercase":
            text = text.lower()
        elif self.text_transform == "capitalize":
            text = text.capitalize()
            
        return text
    
    def to_dict(self) -> Dict[str, Any]:
        """Збереження текстового елементу"""
        base_dict = super().to_dict()
        base_dict.update({
            'text': self.text,
            'font_family': self.font_family,
            'font_size': self.font_size,
            'font_weight': self.font_weight,
            'font_style': self.font_style,
            'text_align': self.text_align,
            'text_decoration': self.text_decoration,
            'line_height': self.line_height,
            'letter_spacing': self.letter_spacing,
            'word_spacing': self.word_spacing,
            'max_lines': self.max_lines,
            'text_transform': self.text_transform,
            'vertical_align': self.vertical_align,
            'white_space': self.white_space,
            'word_wrap': self.word_wrap,
            'text_overflow': self.text_overflow
        })
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TextElement':
        """Відновлення текстового елементу"""
        element = cls(
            text=data.get('text', ''),
            font_family=data.get('font_family', 'Arial'),
            font_size=data.get('font_size', 16)
        )
        
        # Базові властивості
        base_element = ContentElement.from_base_dict(data)
        element.__dict__.update(base_element.__dict__)
        
        # Специфічні текстові властивості
        element.font_weight = data.get('font_weight', 'normal')
        element.font_style = data.get('font_style', 'normal')
        element.text_align = data.get('text_align', 'left')
        element.text_decoration = data.get('text_decoration', 'none')
        element.line_height = data.get('line_height', 1.2)
        element.letter_spacing = data.get('letter_spacing', 0)
        element.word_spacing = data.get('word_spacing', 0)
        element.max_lines = data.get('max_lines')
        element.text_transform = data.get('text_transform', 'none')
        element.vertical_align = data.get('vertical_align', 'top')
        element.white_space = data.get('white_space', 'normal')
        element.word_wrap = data.get('word_wrap', True)
        element.text_overflow = data.get('text_overflow', 'ellipsis')
        
        return element


class ImageElement(ContentElement):
    """Елемент зображення"""
    
    def __init__(self, image_path="", alt_text="", **kwargs):
        super().__init__(element_type="image", **kwargs)
        self.image_path = image_path
        self.original_path = image_path
        self.alt_text = str(alt_text)
        self.fit_mode = "contain"  # contain, cover, fill, scale-down, none
        self.image_quality = 100   # Якість збереження (1-100)
        self.preserve_aspect_ratio = True
        
        # Фільтри та ефекти
        self.filter_effects = {
            'brightness': 100,    # 0-200
            'contrast': 100,      # 0-200  
            'saturation': 100,    # 0-200
            'hue': 0,            # 0-360
            'blur': 0,           # 0-20
            'grayscale': 0,      # 0-100
            'sepia': 0,          # 0-100
            'invert': 0          # 0-100
        }
        
        # Обрізання
        self.crop = {
            'x': 0, 'y': 0, 'width': 100, 'height': 100  # У відсотках
        }
        
        # Метадані зображення
        self.image_info = {
            'format': '',
            'size': (0, 0),
            'file_size': 0,
            'color_mode': '',
            'has_transparency': False
        }
    
    def get_processed_path(self, slide_id: int) -> str:
        """Отримати шлях до обробленого зображення"""
        if not self.image_path:
            return ""
        
        filename, ext = os.path.splitext(os.path.basename(self.image_path))
        processed_filename = f"{filename}_processed_{self.id[:8]}{ext}"
        
        return os.path.join("content", f"slide_{slide_id}", "images", "processed", processed_filename)
    
    def apply_filters(self, slide_id: int) -> bool:
        """Застосувати фільтри до зображення"""
        try:
            from PIL import Image, ImageFilter, ImageEnhance
            
            if not os.path.exists(self.image_path):
                logger.error(f"Зображення не знайдено: {self.image_path}")
                return False
            
            # Відкриваємо оригінальне зображення
            with Image.open(self.image_path) as img:
                processed_img = img.copy()
                
                # Застосовуємо фільтри
                if self.filter_effects['brightness'] != 100:
                    enhancer = ImageEnhance.Brightness(processed_img)
                    processed_img = enhancer.enhance(self.filter_effects['brightness'] / 100)
                
                if self.filter_effects['contrast'] != 100:
                    enhancer = ImageEnhance.Contrast(processed_img)
                    processed_img = enhancer.enhance(self.filter_effects['contrast'] / 100)
                
                if self.filter_effects['saturation'] != 100:
                    enhancer = ImageEnhance.Color(processed_img)
                    processed_img = enhancer.enhance(self.filter_effects['saturation'] / 100)
                
                if self.filter_effects['blur'] > 0:
                    processed_img = processed_img.filter(
                        ImageFilter.GaussianBlur(radius=self.filter_effects['blur'])
                    )
                
                # Сепія
                if self.filter_effects['sepia'] > 0:
                    processed_img = self._apply_sepia(processed_img, self.filter_effects['sepia'])
                
                # Сірий
                if self.filter_effects['grayscale'] > 0:
                    gray_img = processed_img.convert('L').convert('RGB')
                    processed_img = Image.blend(processed_img, gray_img, 
                                              self.filter_effects['grayscale'] / 100)
                
                # Зберігаємо оброблене зображення
                processed_path = self.get_processed_path(slide_id)
                os.makedirs(os.path.dirname(processed_path), exist_ok=True)
                
                processed_img.save(processed_path, quality=self.image_quality)
                
                logger.info(f"Фільтри застосовано: {processed_path}")
                return True
                
        except Exception as e:
            logger.error(f"Помилка застосування фільтрів: {e}")
            return False
    
    def _apply_sepia(self, img, intensity):
        """Застосувати ефект сепії"""
        pixels = img.load()
        for py in range(img.size[1]):
            for px in range(img.size[0]):
                r, g, b = img.getpixel((px, py))[:3]
                
                tr = int(0.393 * r + 0.769 * g + 0.189 * b)
                tg = int(0.349 * r + 0.686 * g + 0.168 * b)
                tb = int(0.272 * r + 0.534 * g + 0.131 * b)
                
                tr = min(255, tr)
                tg = min(255, tg)
                tb = min(255, tb)
                
                # Змішуємо з оригіналом
                mix_r = int(r + (tr - r) * intensity / 100)
                mix_g = int(g + (tg - g) * intensity / 100)
                mix_b = int(b + (tb - b) * intensity / 100)
                
                pixels[px, py] = (mix_r, mix_g, mix_b)
        
        return img
    
    def to_dict(self) -> Dict[str, Any]:
        """Збереження зображення"""
        base_dict = super().to_dict()
        base_dict.update({
            'image_path': self.image_path,
            'original_path': self.original_path,
            'alt_text': self.alt_text,
            'fit_mode': self.fit_mode,
            'image_quality': self.image_quality,
            'preserve_aspect_ratio': self.preserve_aspect_ratio,
            'filter_effects': self.filter_effects,
            'crop': self.crop,
            'image_info': self.image_info
        })
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ImageElement':
        """Відновлення зображення"""
        element = cls(
            image_path=data.get('image_path', ''),
            alt_text=data.get('alt_text', '')
        )
        
        # Базові властивості
        base_element = ContentElement.from_base_dict(data)
        element.__dict__.update(base_element.__dict__)
        
        # Специфічні властивості зображення
        element.original_path = data.get('original_path', '')
        element.fit_mode = data.get('fit_mode', 'contain')
        element.image_quality = data.get('image_quality', 100)
        element.preserve_aspect_ratio = data.get('preserve_aspect_ratio', True)
        element.filter_effects = data.get('filter_effects', {})
        element.crop = data.get('crop', {'x': 0, 'y': 0, 'width': 100, 'height': 100})
        element.image_info = data.get('image_info', {})
        
        return element


class IconElement(ContentElement):
    """Елемент іконки"""
    
    def __init__(self, icon_code="", icon_type="unicode", **kwargs):
        super().__init__(element_type="icon", **kwargs)
        self.icon_code = str(icon_code)
        self.icon_type = icon_type  # unicode, fontawesome, material, custom, emoji
        self.icon_family = "Arial"
        self.icon_size = 24
        self.icon_color = "#000000"
        self.icon_library = ""  # Бібліотека іконок
        self.icon_variant = "regular"  # regular, solid, light, duotone
        
        # Для кастомних іконок
        self.custom_svg_path = ""
        self.custom_image_path = ""
    
    def get_display_value(self) -> str:
        """Отримати значення для відображення"""
        if self.icon_type == "unicode" or self.icon_type == "emoji":
            return self.icon_code
        elif self.icon_type == "fontawesome":
            return f"fa-{self.icon_code}"
        elif self.icon_type == "material":
            return self.icon_code
        else:
            return self.icon_code
    
    def to_dict(self) -> Dict[str, Any]:
        """Збереження іконки"""
        base_dict = super().to_dict()
        base_dict.update({
            'icon_code': self.icon_code,
            'icon_type': self.icon_type,
            'icon_family': self.icon_family,
            'icon_size': self.icon_size,
            'icon_color': self.icon_color,
            'icon_library': self.icon_library,
            'icon_variant': self.icon_variant,
            'custom_svg_path': self.custom_svg_path,
            'custom_image_path': self.custom_image_path
        })
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'IconElement':
        """Відновлення іконки"""
        element = cls(
            icon_code=data.get('icon_code', ''),
            icon_type=data.get('icon_type', 'unicode')
        )
        
        # Базові властивості
        base_element = ContentElement.from_base_dict(data)
        element.__dict__.update(base_element.__dict__)
        
        # Специфічні властивості іконки
        element.icon_family = data.get('icon_family', 'Arial')
        element.icon_size = data.get('icon_size', 24)
        element.icon_color = data.get('icon_color', '#000000')
        element.icon_library = data.get('icon_library', '')
        element.icon_variant = data.get('icon_variant', 'regular')
        element.custom_svg_path = data.get('custom_svg_path', '')
        element.custom_image_path = data.get('custom_image_path', '')
        
        return element


class SymbolElement(ContentElement):
    """Елемент символу/емодзі"""
    
    def __init__(self, symbol="", symbol_type="emoji", **kwargs):
        super().__init__(element_type="symbol", **kwargs)
        self.symbol = str(symbol)
        self.symbol_type = symbol_type  # emoji, mathematical, geometric, currency, arrow
        self.symbol_size = 24
        self.symbol_unicode = ""
        self.symbol_name = ""
        self.symbol_category = ""
        
        # Для математичних символів
        self.math_notation = ""
        self.latex_code = ""
    
    def get_unicode_info(self) -> Dict[str, str]:
        """Отримати інформацію про Unicode"""
        if self.symbol:
            unicode_code = ord(self.symbol[0]) if len(self.symbol) > 0 else 0
            return {
                'decimal': str(unicode_code),
                'hex': f"U+{unicode_code:04X}",
                'html': f"&#{unicode_code};",
                'css': f"\\{unicode_code:04X}"
            }
        return {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Збереження символу"""
        base_dict = super().to_dict()
        base_dict.update({
            'symbol': self.symbol,
            'symbol_type': self.symbol_type,
            'symbol_size': self.symbol_size,
            'symbol_unicode': self.symbol_unicode,
            'symbol_name': self.symbol_name,
            'symbol_category': self.symbol_category,
            'math_notation': self.math_notation,
            'latex_code': self.latex_code,
            'unicode_info': self.get_unicode_info()
        })
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SymbolElement':
        """Відновлення символу"""
        element = cls(
            symbol=data.get('symbol', ''),
            symbol_type=data.get('symbol_type', 'emoji')
        )
        
        # Базові властивості
        base_element = ContentElement.from_base_dict(data)
        element.__dict__.update(base_element.__dict__)
        
        # Специфічні властивості символу
        element.symbol_size = data.get('symbol_size', 24)
        element.symbol_unicode = data.get('symbol_unicode', '')
        element.symbol_name = data.get('symbol_name', '')
        element.symbol_category = data.get('symbol_category', '')
        element.math_notation = data.get('math_notation', '')
        element.latex_code = data.get('latex_code', '')
        
        return element


# =====================================================================
# ОСНОВНІ КЛАСИ СЛАЙДІВ ТА МЕНЕДЖЕРА
# =====================================================================

class SlideData:
    """Розширений клас слайду з повною підтримкою всіх елементів"""
    
    def __init__(self, slide_id: int, title: str = "", background_color: str = "#ffffff"):
        self.slide_id = int(slide_id)
        self.title = str(title)
        self.background_color = background_color
        self.background_image = None
        self.background_gradient = None
        self.last_modified = datetime.now()
        self.version = 1
        self.created_at = datetime.now()
        
        # Зберігання елементів
        self.elements: Dict[str, ContentElement] = {}
        self.element_order: List[str] = []
        
        # Налаштування слайду
        self.config = {
            'width': DEFAULT_SLIDE_WIDTH,
            'height': DEFAULT_SLIDE_HEIGHT,
            'animation_in': 'none',
            'animation_out': 'none',
            'duration': 5000,
            'auto_advance': False,
            'transition': 'none',
            'background_music': None,
            'notes': ''
        }
        
        # Історія змін (для версіонування)
        self.change_history: List[Dict[str, Any]] = []
    
    def add_text_element(self, text: str, x: float = 0, y: float = 0, 
                        width: float = 200, height: float = 50, **options) -> str:
        """Додати текстовий елемент"""
        element = TextElement(
            text=text, x=x, y=y, width=width, height=height, **options
        )
        
        self.elements[element.id] = element
        self.element_order.append(element.id)
        self._add_to_history('add_element', element.id, {'type': 'text', 'text': text})
        self._update_modified()
        
        logger.info(f"Додано текстовий елемент на слайд {self.slide_id}: {text[:50]}")
        return element.id
    
    def add_image_element(self, image_path: str, x: float = 0, y: float = 0,
                         width: float = 100, height: float = 100, **options) -> Optional[str]:
        """Додати зображення"""
        if not os.path.exists(image_path):
            logger.error(f"Файл зображення не знайдено: {image_path}")
            return None
        
        # Копіюємо зображення
        copied_path = self._copy_image_to_slide_folder(image_path)
        if not copied_path:
            return None
        
        element = ImageElement(
            image_path=copied_path, x=x, y=y, width=width, height=height, **options
        )
        element.original_path = image_path
        
        # Отримуємо інформацію про зображення
        element.image_info = self._get_image_info(image_path)
        
        self.elements[element.id] = element
        self.element_order.append(element.id)
        self._add_to_history('add_element', element.id, {'type': 'image', 'path': image_path})
        self._update_modified()
        
        # Застосовуємо фільтри якщо потрібно
        element.apply_filters(self.slide_id)
        
        logger.info(f"Додано зображення на слайд {self.slide_id}: {os.path.basename(image_path)}")
        return element.id
    
    def add_icon_element(self, icon_code: str, x: float = 0, y: float = 0, 
                        size: int = 24, **options) -> str:
        """Додати іконку"""
        element = IconElement(
            icon_code=icon_code, x=x, y=y, width=size, height=size, **options
        )
        element.icon_size = size
        
        self.elements[element.id] = element
        self.element_order.append(element.id)
        self._add_to_history('add_element', element.id, {'type': 'icon', 'code': icon_code})
        self._update_modified()
        
        logger.info(f"Додано іконку на слайд {self.slide_id}: {icon_code}")
        return element.id
    
    def add_symbol_element(self, symbol: str, x: float = 0, y: float = 0,
                          size: int = 24, **options) -> str:
        """Додати символ/емодзі"""
        element = SymbolElement(
            symbol=symbol, x=x, y=y, width=size, height=size, **options
        )
        element.symbol_size = size
        
        # Автоматично визначаємо тип символу
        if self._is_emoji(symbol):
            element.symbol_type = "emoji"
        elif self._is_mathematical_symbol(symbol):
            element.symbol_type = "mathematical"
        
        self.elements[element.id] = element
        self.element_order.append(element.id)
        self._add_to_history('add_element', element.id, {'type': 'symbol', 'symbol': symbol})
        self._update_modified()
        
        logger.info(f"Додано символ на слайд {self.slide_id}: {symbol}")
        return element.id
    
    def remove_element(self, element_id: str) -> bool:
        """Видалити елемент"""
        if element_id not in self.elements:
            return False
        
        element = self.elements[element_id]
        
        # Зберігаємо в історії перед видаленням
        self._add_to_history('remove_element', element_id, element.to_dict())
        
        # Видаляємо пов'язані файли
        if element.type == "image" and hasattr(element, 'image_path'):
            self._remove_image_files(element)
        
        # Видаляємо елемент
        del self.elements[element_id]
        if element_id in self.element_order:
            self.element_order.remove(element_id)
        
        self._update_modified()
        logger.info(f"Видалено елемент {element_id} з слайду {self.slide_id}")
        return True
    
    def update_element(self, element_id: str, **updates) -> bool:
        """Оновити елемент"""
        if element_id not in self.elements:
            return False
        
        element = self.elements[element_id]
        old_data = element.to_dict()
        
        # Застосовуємо оновлення
        for key, value in updates.items():
            if hasattr(element, key):
                setattr(element, key, value)
        
        element.modified_at = datetime.now()
        
        # Для зображень застосовуємо фільтри при зміні
        if element.type == "image" and any(key.startswith('filter_') for key in updates.keys()):
            element.apply_filters(self.slide_id)
        
        self._add_to_history('update_element', element_id, {
            'old': old_data,
            'new': updates
        })
        self._update_modified()
        
        logger.debug(f"Оновлено елемент {element_id} на слайді {self.slide_id}")
        return True
    
    def reorder_element(self, element_id: str, new_z_index: int) -> bool:
        """Змінити порядок елемента"""
        if element_id not in self.elements:
            return False
        
        old_z_index = self.elements[element_id].z_index
        self.elements[element_id].z_index = new_z_index
        
        # Пересортовуємо
        self.element_order.sort(key=lambda eid: self.elements[eid].z_index)
        
        self._add_to_history('reorder_element', element_id, {
            'old_z_index': old_z_index,
            'new_z_index': new_z_index
        })
        self._update_modified()
        
        logger.debug(f"Змінено z-index елемента {element_id}: {old_z_index} -> {new_z_index}")
        return True
    
    def get_elements_by_type(self, element_type: str) -> Dict[str, ContentElement]:
        """Отримати елементи за типом"""
        return {eid: elem for eid, elem in self.elements.items() 
                if elem.type == element_type}
    
    def get_all_text_content(self) -> str:
        """Отримати весь текстовий контент слайду"""
        text_elements = self.get_elements_by_type("text")
        return "\n".join([elem.text for elem in text_elements.values()])
    
    def get_slide_statistics(self) -> Dict[str, Any]:
        """Отримати статистику слайду"""
        stats = {
            'total_elements': len(self.elements),
            'by_type': {},
            'total_characters': 0,
            'total_words': 0,
            'image_count': 0,
            'file_sizes': {}
        }
        
        for element in self.elements.values():
            stats['by_type'][element.type] = stats['by_type'].get(element.type, 0) + 1
            
            if element.type == "text":
                stats['total_characters'] += len(element.text)
                stats['total_words'] += len(element.text.split())
            elif element.type == "image":
                stats['image_count'] += 1
        
        return stats
    
    def create_processed_version(self) -> Dict[str, Any]:
        """Створити оброблену версію слайду для показу"""
        processed_data = {
            'slide_id': self.slide_id,
            'title': self.title,
            'background': {
                'color': self.background_color,
                'image': self.background_image,
                'gradient': self.background_gradient
            },
            'config': self.config.copy(),
            'elements': {},
            'element_order': self.element_order.copy(),
            'processed_at': datetime.now().isoformat(),
            'version': self.version
        }
        
        # Обробляємо кожен елемент
        for element_id, element in self.elements.items():
            processed_element = element.to_dict()
            
            # Спеціальна обробка для зображень
            if element.type == "image":
                # Використовуємо оброблену версію якщо є
                processed_path = element.get_processed_path(self.slide_id)
                if os.path.exists(processed_path):
                    processed_element['display_path'] = processed_path
                else:
                    processed_element['display_path'] = element.image_path
                
                # Додаємо мініатюру
                processed_element['thumbnail'] = self._create_thumbnail(element)
            
            # Обробка тексту для відображення
            elif element.type == "text":
                processed_element['formatted_text'] = element.get_formatted_text()
            
            processed_data['elements'][element_id] = processed_element
        
        return processed_data
    
    def _copy_image_to_slide_folder(self, image_path: str) -> Optional[str]:
        """Копіювати зображення в папку слайду"""
        try:
            # Перевірка формату
            file_ext = os.path.splitext(image_path)[1].lower()
            if file_ext not in SUPPORTED_IMAGE_FORMATS:
                logger.error(f"Непідтримуваний формат зображення: {file_ext}")
                return None
            
            # Створюємо структуру папок
            slide_dir = os.path.join("content", f"slide_{self.slide_id}", "images", "original")
            os.makedirs(slide_dir, exist_ok=True)
            
            # Унікальне ім'я файлу
            filename = f"{uuid.uuid4()}_{os.path.basename(image_path)}"
            dest_path = os.path.join(slide_dir, filename)
            
            # Копіюємо файл
            shutil.copy2(image_path, dest_path)
            
            # Повертаємо відносний шлях
            relative_path = os.path.relpath(dest_path, "content")
            
            logger.info(f"Зображення скопійовано: {image_path} -> {dest_path}")
            return relative_path
            
        except Exception as e:
            logger.error(f"Помилка копіювання зображення: {e}")
            return None
    
    def _remove_image_files(self, image_element: ImageElement) -> None:
        """Видалити файли зображення"""
        try:
            # Оригінальний файл
            if image_element.image_path:
                full_path = os.path.join("content", image_element.image_path)
                if os.path.exists(full_path):
                    os.remove(full_path)
            
            # Оброблена версія
            processed_path = image_element.get_processed_path(self.slide_id)
            if os.path.exists(processed_path):
                os.remove(processed_path)
            
            # Мініатюра
            thumbnail_path = self._get_thumbnail_path(image_element)
            if os.path.exists(thumbnail_path):
                os.remove(thumbnail_path)
                
        except Exception as e:
            logger.error(f"Помилка видалення файлів зображення: {e}")
    
    def _get_image_info(self, image_path: str) -> Dict[str, Any]:
        """Отримати інформацію про зображення"""
        try:
            from PIL import Image
            
            with Image.open(image_path) as img:
                return {
                    'format': img.format,
                    'size': img.size,
                    'file_size': os.path.getsize(image_path),
                    'color_mode': img.mode,
                    'has_transparency': 'transparency' in img.info
                }
        except Exception as e:
            logger.error(f"Помилка отримання інформації про зображення: {e}")
            return {}
    
    def _create_thumbnail(self, image_element: ImageElement) -> str:
        """Створити мініатюру зображення"""
        try:
            from PIL import Image
            
            thumbnail_path = self._get_thumbnail_path(image_element)
            
            if os.path.exists(thumbnail_path):
                return thumbnail_path
            
            # Створюємо мініатюру
            full_image_path = os.path.join("content", image_element.image_path)
            
            with Image.open(full_image_path) as img:
                img.thumbnail((150, 150), Image.Resampling.LANCZOS)
                
                os.makedirs(os.path.dirname(thumbnail_path), exist_ok=True)
                img.save(thumbnail_path, quality=85)
            
            return thumbnail_path
            
        except Exception as e:
            logger.error(f"Помилка створення мініатюри: {e}")
            return ""
    
    def _get_thumbnail_path(self, image_element: ImageElement) -> str:
        """Отримати шлях до мініатюри"""
        filename = f"thumb_{image_element.id[:8]}.jpg"
        return os.path.join("content", f"slide_{self.slide_id}", "images", "thumbnails", filename)
    
    def _is_emoji(self, text: str) -> bool:
        """Перевірити чи є символ емодзі"""
        import unicodedata
        for char in text:
            if unicodedata.category(char) == 'So':  # Symbol, other
                return True
        return False
    
    def _is_mathematical_symbol(self, text: str) -> bool:
        """Перевірити чи є символ математичним"""
        math_ranges = [
            (0x2200, 0x22FF),  # Mathematical Operators
            (0x2190, 0x21FF),  # Arrows
            (0x27C0, 0x27EF),  # Miscellaneous Mathematical Symbols-A
            (0x2980, 0x29FF),  # Miscellaneous Mathematical Symbols-B
        ]
        
        for char in text:
            code = ord(char)
            for start, end in math_ranges:
                if start <= code <= end:
                    return True
        return False
    
    def _add_to_history(self, action: str, element_id: str, data: Dict[str, Any]) -> None:
        """Додати зміну в історію"""
        self.change_history.append({
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'element_id': element_id,
            'data': data,
            'version': self.version
        })
        
        # Обмежуємо історію (останні 100 змін)
        if len(self.change_history) > 100:
            self.change_history = self.change_history[-100:]
    
    def _update_modified(self) -> None:
        """Оновити час модифікації та версію"""
        self.last_modified = datetime.now()
        self.version += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Повне збереження слайду"""
        return {
            'slide_id': self.slide_id,
            'title': self.title,
            'background_color': self.background_color,
            'background_image': self.background_image,
            'background_gradient': self.background_gradient,
            'created_at': self.created_at.isoformat(),
            'last_modified': self.last_modified.isoformat(),
            'version': self.version,
            'config': self.config,
            'elements': {eid: elem.to_dict() for eid, elem in self.elements.items()},
            'element_order': self.element_order,
            'change_history': self.change_history[-10:],  # Останні 10 змін
            'statistics': self.get_slide_statistics()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SlideData':
        """Відновлення слайду зі словника"""
        slide = cls(
            data.get('slide_id', 1),
            data.get('title', ''),
            data.get('background_color', '#ffffff')
        )
        
        slide.background_image = data.get('background_image')
        slide.background_gradient = data.get('background_gradient')
        slide.version = data.get('version', 1)
        slide.config = data.get('config', {})
        slide.element_order = data.get('element_order', [])
        slide.change_history = data.get('change_history', [])
        
        # Відновлення часу
        try:
            slide.created_at = datetime.fromisoformat(data.get('created_at', datetime.now().isoformat()))
            slide.last_modified = datetime.fromisoformat(data.get('last_modified', datetime.now().isoformat()))
        except:
            slide.created_at = slide.last_modified = datetime.now()
        
        # Відновлення елементів
        elements_data = data.get('elements', {})
        for element_id, element_data in elements_data.items():
            element_type = element_data.get('type', 'text')
            
            if element_type == "text":
                element = TextElement.from_dict(element_data)
            elif element_type == "image":
                element = ImageElement.from_dict(element_data)
            elif element_type == "icon":
                element = IconElement.from_dict(element_data)
            elif element_type == "symbol":
                element = SymbolElement.from_dict(element_data)
            else:
                continue
            
            slide.elements[element_id] = element
        
        return slide


# =====================================================================
# ГОЛОВНИЙ МЕНЕДЖЕР КОНТЕНТУ
# =====================================================================

class ContentManager:
    """Повний менеджер контенту з підтримкою всіх елементів"""
    
    def __init__(self):
        self.slides: Dict[int, SlideData] = {}
        self.content_observers: List[callable] = []
        self.media_base_path = "content"
        self.current_slide_id = 1
        self.presentation_metadata = {
            'title': 'BumbleB Dynamic Presentation',
            'author': 'Bertrandt',
            'version': '4.0.0',
            'created_at': datetime.now().isoformat(),
            'last_saved': None,
            'total_slides': 0,
            'template': 'bertrandt_dark'
        }
        
        # Ініціалізація
        self._ensure_directory_structure()
        self.load_default_content()
    
    def _ensure_directory_structure(self) -> None:
        """Створити структуру директорій"""
        directories = [
            "content",
            "content/templates",
            "data",
            "data/backups", 
            "data/exports",
            "logs"
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    def load_default_content(self) -> None:
        """Завантаження базового контенту"""
        default_slides_data = [
            {
                'id': 1,
                'title': 'BumbleB - Das automatisierte Shuttle',
                'content': [
                    {'type': 'text', 'text': 'BumbleB - Das automatisierte Shuttle', 
                     'x': 100, 'y': 80, 'font_size': 36, 'font_weight': 'bold'},
                    {'type': 'text', 'text': 'Schonmal ein automatisiert Shuttle gesehen, das aussieht wie eine Hummel?',
                     'x': 100, 'y': 200, 'font_size': 18},
                    {'type': 'symbol', 'symbol': '🐝', 'x': 800, 'y': 80, 'size': 64},
                    {'type': 'symbol', 'symbol': '🚌', 'x': 800, 'y': 180, 'size': 48}
                ]
            },
            {
                'id': 2,
                'title': 'BumbleB - Wie die Hummel fährt',
                'content': [
                    {'type': 'text', 'text': 'BumbleB - Wie die Hummel fährt',
                     'x': 100, 'y': 80, 'font_size': 36, 'font_weight': 'bold'},
                    {'type': 'text', 'text': 'Innovative Technologie für autonomes Fahren',
                     'x': 100, 'y': 200, 'font_size': 20},
                    {'type': 'icon', 'icon_code': '⚡', 'x': 800, 'y': 100, 'size': 48},
                    {'type': 'icon', 'icon_code': '🔧', 'x': 800, 'y': 180, 'size': 40}
                ]
            },
            {
                'id': 3,
                'title': 'Einsatzgebiete und Vorteile',
                'content': [
                    {'type': 'text', 'text': 'Einsatzgebiete und Vorteile',
                     'x': 100, 'y': 80, 'font_size': 36, 'font_weight': 'bold'},
                    {'type': 'text', 'text': '• Urbane Gebiete\n• Nachhaltiger Transport\n• Vielseitige Einsatzmöglichkeiten',
                     'x': 100, 'y': 200, 'font_size': 18, 'line_height': 1.5},
                    {'type': 'symbol', 'symbol': '🏙️', 'x': 600, 'y': 180, 'size': 48},
                    {'type': 'symbol', 'symbol': '♻️', 'x': 700, 'y': 180, 'size': 48},
                    {'type': 'symbol', 'symbol': '🚀', 'x': 800, 'y': 180, 'size': 48}
                ]
            },
            {
                'id': 4,
                'title': 'Sicherheitssysteme',
                'content': [
                    {'type': 'text', 'text': 'Sicherheitssysteme',
                     'x': 100, 'y': 80, 'font_size': 36, 'font_weight': 'bold'},
                    {'type': 'text', 'text': 'Maximale Sicherheit für alle Passagiere',
                     'x': 100, 'y': 200, 'font_size': 20},
                    {'type': 'symbol', 'symbol': '🛡️', 'x': 600, 'y': 150, 'size': 64},
                    {'type': 'icon', 'icon_code': '✓', 'x': 700, 'y': 180, 'size': 32},
                    {'type': 'symbol', 'symbol': '📡', 'x': 800, 'y': 150, 'size': 48}
                ]
            },
            {
                'id': 5,
                'title': 'Nachhaltigkeit & Umwelt',
                'content': [
                    {'type': 'text', 'text': 'Nachhaltigkeit & Umwelt',
                     'x': 100, 'y': 80, 'font_size': 36, 'font_weight': 'bold'},
                    {'type': 'text', 'text': 'Umweltfreundlich und effizient für eine grüne Zukunft',
                     'x': 100, 'y': 200, 'font_size': 18},
                    {'type': 'symbol', 'symbol': '🌱', 'x': 600, 'y': 150, 'size': 56},
                    {'type': 'symbol', 'symbol': '🌍', 'x': 700, 'y': 150, 'size': 56},
                    {'type': 'symbol', 'symbol': '💚', 'x': 800, 'y': 150, 'size': 48}
                ]
            }
        ]
        
        # Створюємо слайди з контентом
        for slide_data in default_slides_data:
            if slide_data['id'] not in self.slides:
                slide = SlideData(slide_data['id'], slide_data['title'])
                
                # Додаємо елементи
                for content_item in slide_data['content']:
                    if content_item['type'] == 'text':
                        slide.add_text_element(
                            content_item['text'],
                            x=content_item['x'],
                            y=content_item['y'],
                            font_size=content_item.get('font_size', 16),
                            font_weight=content_item.get('font_weight', 'normal'),
                            line_height=content_item.get('line_height', 1.2)
                        )
                    elif content_item['type'] == 'symbol':
                        slide.add_symbol_element(
                            content_item['symbol'],
                            x=content_item['x'],
                            y=content_item['y'],
                            size=content_item['size']
                        )
                    elif content_item['type'] == 'icon':
                        slide.add_icon_element(
                            content_item['icon_code'],
                            x=content_item['x'],
                            y=content_item['y'],
                            size=content_item['size']
                        )
                
                self.slides[slide_data['id']] = slide
        
        self.presentation_metadata['total_slides'] = len(self.slides)
        logger.info(f"Завантажено {len(self.slides)} слайдів за замовчуванням")
    
    # =====================================================================
    # ОСНОВНІ МЕТОДИ УПРАВЛІННЯ СЛАЙДАМИ
    # =====================================================================
    
    def get_slide(self, slide_id: int) -> Optional[SlideData]:
        """Отримати слайд за ID"""
        return self.slides.get(slide_id)
    
    def get_all_slides(self) -> Dict[int, SlideData]:
        """Отримати всі слайди"""
        return self.slides.copy()
    
    def create_slide(self, slide_id: int = None, title: str = "") -> int:
        """Створити новий слайд"""
        if slide_id is None:
            slide_id = max(self.slides.keys(), default=0) + 1
        
        if slide_id in self.slides:
            logger.warning(f"Слайд {slide_id} вже існує")
            return slide_id
        
        self.slides[slide_id] = SlideData(slide_id, title)
        self.presentation_metadata['total_slides'] = len(self.slides)
        
        self.notify_observers(slide_id, self.slides[slide_id], action='create')
        logger.info(f"Створено новий слайд {slide_id}: {title}")
        
        return slide_id
    
    def delete_slide(self, slide_id: int) -> bool:
        """Видалити слайд"""
        if slide_id not in self.slides:
            return False
        
        slide = self.slides[slide_id]
        
        # Видаляємо всі пов'язані файли
        for element in slide.elements.values():
            if element.type == "image":
                slide._remove_image_files(element)
        
        del self.slides[slide_id]
        self.presentation_metadata['total_slides'] = len(self.slides)
        
        self.notify_observers(slide_id, None, action='delete')
        logger.info(f"Видалено слайд {slide_id}")
        
        return True
    
    # =====================================================================
    # МЕТОДИ ДОДАВАННЯ КОНТЕНТУ
    # =====================================================================
    
    def add_text_to_slide(self, slide_id: int, text: str, x: float = 0, 
                         y: float = 0, **options) -> Optional[str]:
        """Додати текст до слайду"""
        slide = self.get_slide(slide_id)
        if not slide:
            logger.error(f"Слайд {slide_id} не знайдено")
            return None
        
        element_id = slide.add_text_element(text, x, y, **options)
        self.notify_observers(slide_id, slide, action='update')
        
        return element_id
    
    def add_image_to_slide(self, slide_id: int, image_path: str, x: float = 0,
                          y: float = 0, **options) -> Optional[str]:
        """Додати зображення до слайду"""
        slide = self.get_slide(slide_id)
        if not slide:
            logger.error(f"Слайд {slide_id} не знайдено")
            return None
        
        element_id = slide.add_image_element(image_path, x, y, **options)
        if element_id:
            self.notify_observers(slide_id, slide, action='update')
        
        return element_id
    
    def add_icon_to_slide(self, slide_id: int, icon_code: str, x: float = 0,
                         y: float = 0, **options) -> Optional[str]:
        """Додати іконку до слайду"""
        slide = self.get_slide(slide_id)
        if not slide:
            logger.error(f"Слайд {slide_id} не знайдено")
            return None
        
        element_id = slide.add_icon_element(icon_code, x, y, **options)
        self.notify_observers(slide_id, slide, action='update')
        
        return element_id
    
    def add_symbol_to_slide(self, slide_id: int, symbol: str, x: float = 0,
                           y: float = 0, **options) -> Optional[str]:
        """Додати символ/емодзі до слайду"""
        slide = self.get_slide(slide_id)
        if not slide:
            logger.error(f"Слайд {slide_id} не знайдено")
            return None
        
        element_id = slide.add_symbol_element(symbol, x, y, **options)
        self.notify_observers(slide_id, slide, action='update')
        
        return element_id
    
    # =====================================================================
    # МЕТОДИ ЗБЕРЕЖЕННЯ ТА ЗАВАНТАЖЕННЯ
    # =====================================================================
    
    def save_presentation(self, filepath: str = None) -> Optional[str]:
        """Повне збереження презентації"""
        if not filepath:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = os.path.join("data", f"presentation_{timestamp}.json")
        
        # Оновлюємо метадані
        self.presentation_metadata['last_saved'] = datetime.now().isoformat()
        self.presentation_metadata['total_slides'] = len(self.slides)
        
        presentation_data = {
            'metadata': self.presentation_metadata,
            'slides': {str(k): v.to_dict() for k, v in self.slides.items()},
            'media_base_path': self.media_base_path,
            'version_info': {
                'content_manager_version': '4.0.0',
                'format_version': '1.0',
                'python_version': '3.8+',
                'required_libraries': ['PIL', 'tkinter']
            }
        }
        
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(presentation_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Презентацію збережено: {filepath}")
            
            # Створюємо повний архів
            backup_path = self._create_complete_backup(filepath)
            
            # Створюємо оброблені версії слайдів
            self._create_processed_versions(filepath)
            
            return filepath
            
        except Exception as e:
            logger.error(f"❌ Помилка збереження презентації: {e}")
            return None
    
    def load_presentation(self, filepath: str) -> bool:
        """Завантаження презентації"""
        if not os.path.exists(filepath):
            logger.error(f"Файл не знайдено: {filepath}")
            return False
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Завантажуємо метадані
            self.presentation_metadata = data.get('metadata', {})
            self.media_base_path = data.get('media_base_path', 'content')
            
            # Очищуємо поточні слайди
            self.slides.clear()
            
            # Завантажуємо слайди
            slides_data = data.get('slides', {})
            for slide_id_str, slide_data in slides_data.items():
                slide_id = int(slide_id_str)
                self.slides[slide_id] = SlideData.from_dict(slide_data)
            
            logger.info(f"✅ Завантажено {len(self.slides)} слайдів з {filepath}")
            
            # Сповіщаємо спостерігачів
            for slide_id, slide_data in self.slides.items():
                self.notify_observers(slide_id, slide_data, action='load')
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Помилка завантаження презентації: {e}")
            return False
    
    def _create_complete_backup(self, json_filepath: str) -> str:
        """Створити повний архів з медіафайлами"""
        try:
            backup_path = json_filepath.replace('.json', '_complete.zip')
            
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Додаємо JSON файл
                zipf.write(json_filepath, os.path.basename(json_filepath))
                
                # Додаємо всі медіафайли
                for slide in self.slides.values():
                    for element in slide.elements.values():
                        if element.type == "image" and hasattr(element, 'image_path'):
                            
                            # Оригінальний файл
                            original_path = os.path.join("content", element.image_path)
                            if os.path.exists(original_path):
                                zipf.write(original_path, element.image_path)
                            
                            # Оброблена версія
                            processed_path = element.get_processed_path(slide.slide_id)
                            if os.path.exists(processed_path):
                                arcname = f"processed/{os.path.basename(processed_path)}"
                                zipf.write(processed_path, arcname)
                            
                            # Мініатюра
                            thumbnail_path = slide._get_thumbnail_path(element)
                            if os.path.exists(thumbnail_path):
                                arcname = f"thumbnails/{os.path.basename(thumbnail_path)}"
                                zipf.write(thumbnail_path, arcname)
            
            logger.info(f"✅ Створено повний архів: {backup_path}")
            return backup_path
            
        except Exception as e:
            logger.error(f"⚠️ Помилка створення архіву: {e}")
            return ""
    
    def _create_processed_versions(self, json_filepath: str) -> str:
        """Створити оброблені версії для показу"""
        try:
            processed_dir = os.path.join(os.path.dirname(json_filepath), "processed")
            os.makedirs(processed_dir, exist_ok=True)
            
            processed_data = {
                'presentation_info': self.presentation_metadata,
                'slides': {},
                'created_at': datetime.now().isoformat()
            }
            
            # Створюємо оброблені версії кожного слайду
            for slide_id, slide in self.slides.items():
                processed_data['slides'][str(slide_id)] = slide.create_processed_version()
            
            processed_filepath = os.path.join(processed_dir, "processed_presentation.json")
            
            with open(processed_filepath, 'w', encoding='utf-8') as f:
                json.dump(processed_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Створено оброблені версії: {processed_filepath}")
            return processed_filepath
            
        except Exception as e:
            logger.error(f"⚠️ Помилка створення оброблених версій: {e}")
            return ""
    
    # =====================================================================
    # МЕТОДИ ЕКСПОРТУ
    # =====================================================================
    
    def export_to_yaml(self, filepath: str = None) -> Optional[str]:
        """Експорт в YAML формат"""
        if not filepath:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = os.path.join("data", "exports", f"presentation_{timestamp}.yaml")
        
        presentation_data = {
            'metadata': self.presentation_metadata,
            'slides': {str(k): v.to_dict() for k, v in self.slides.items()},
            'exported_at': datetime.now().isoformat()
        }
        
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                yaml.dump(presentation_data, f, default_flow_style=False, 
                         allow_unicode=True, indent=2)
            
            logger.info(f"✅ Експорт в YAML: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"❌ Помилка експорту в YAML: {e}")
            return None
    
    def get_presentation_statistics(self) -> Dict[str, Any]:
        """Отримати загальну статистику презентації"""
        total_elements = 0
        elements_by_type = {}
        total_text_chars = 0
        total_images = 0
        
        for slide in self.slides.values():
            slide_stats = slide.get_slide_statistics()
            total_elements += slide_stats['total_elements']
            total_text_chars += slide_stats['total_characters']
            total_images += slide_stats['image_count']
            
            for element_type, count in slide_stats['by_type'].items():
                elements_by_type[element_type] = elements_by_type.get(element_type, 0) + count
        
        return {
            'total_slides': len(self.slides),
            'total_elements': total_elements,
            'elements_by_type': elements_by_type,
            'total_text_characters': total_text_chars,
            'total_images': total_images,
            'presentation_info': self.presentation_metadata
        }
    
    # =====================================================================
    # СПОСТЕРІГАЧІ ТА СПОВІЩЕННЯ
    # =====================================================================
    
    def add_observer(self, callback: callable) -> None:
        """Додати спостерігача"""
        if callback not in self.content_observers:
            self.content_observers.append(callback)
    
    def remove_observer(self, callback: callable) -> None:
        """Видалити спостерігача"""
        if callback in self.content_observers:
            self.content_observers.remove(callback)
    
    def notify_observers(self, slide_id: int, slide_data: Optional[SlideData], 
                        action: str = 'update') -> None:
        """Сповістити всіх спостерігачів"""
        for callback in self.content_observers:
            try:
                callback(slide_id, slide_data, action)
            except Exception as e:
                logger.error(f"Помилка сповіщення спостерігача: {e}")


# =====================================================================
# ГЛОБАЛЬНА ІНСТАНЦІЯ ТА ДОПОМІЖНІ ФУНКЦІЇ
# =====================================================================

# Глобальна інстанція менеджера контенту
content_manager = ContentManager()


def quick_save() -> bool:
    """Швидке збереження поточної презентації"""
    try:
        filepath = content_manager.save_presentation()
        return filepath is not None
    except Exception as e:
        logger.error(f"Помилка швидкого збереження: {e}")
        return False


def quick_load(filepath: str) -> bool:
    """Швидке завантаження презентації"""
    try:
        return content_manager.load_presentation(filepath)
    except Exception as e:
        logger.error(f"Помилка швидкого завантаження: {e}")
        return False


# =====================================================================
# ТЕСТУВАННЯ ТА ДЕМОНСТРАЦІЯ
# =====================================================================

if __name__ == "__main__":
    # Демонстрація роботи системи
    print("🎯 Тестування Content Manager v4.0")
    print("=" * 50)
    
    # Створюємо менеджер
    cm = ContentManager()
    
    # Отримуємо слайд для тестування
    test_slide = cm.get_slide(1)
    if test_slide:
        print(f"📄 Тестовий слайд: {test_slide.title}")
        print(f"   Елементів: {len(test_slide.elements)}")
        
        # Додаємо різні типи контенту
        test_slide.add_text_element("Тестовий текст 🎉", x=50, y=300, font_size=20)
        test_slide.add_symbol_element("⭐", x=400, y=300, size=32)
        test_slide.add_icon_element("✓", x=450, y=300, size=28)
        
        print(f"   Після додавання: {len(test_slide.elements)} елементів")
    
    # Зберігаємо презентацію
    saved_path = cm.save_presentation()
    if saved_path:
        print(f"💾 Збережено в: {saved_path}")
        
        # Статистика
        stats = cm.get_presentation_statistics()
        print(f"📊 Статистика:")
        print(f"   Слайдів: {stats['total_slides']}")
        print(f"   Елементів: {stats['total_elements']}")
        print(f"   По типах: {stats['elements_by_type']}")
    
    print("\n✅ Тестування завершено!")
