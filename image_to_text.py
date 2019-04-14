try:
    from PIL import Image
except ImportError:
    import Image
import pytesseract

pytesseract.pytesseract.tesseract_cmd = r'C:\\Program Files (x86)\\Tesseract-OCR\\tesseract.exe'

def change_contrast(img, level):
    factor = (259 * (level + 255)) / (255 * (259 - level))
    def contrast(c):
        return 128 + factor * (c - 128)
    return img.point(contrast)


img = Image.open('test_files\\real_scan\\norm.png')
img_2 = change_contrast(img, 30)
img_2.save("tmp.png")
print(type(pytesseract.image_to_string(img_2, lang='rus+eng')))
