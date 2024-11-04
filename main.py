from os.path import isdir
import re
import pymupdf
from pathlib import Path
import json
import pytesseract
import os, sys
from PIL import Image
from rich.panel import Panel 
from rich import print
from rich.pretty import Pretty
from rich.console import Console
from rich.align import Align
from rich.text import Text
import rich
from threading import Thread
from concurrent.futures import ThreadPoolExecutor
#r = request
#q = question
#n = notification
#pt = prompt_text
#a = answer


config = {}
def start() -> tuple[list[str] , bool]:
    file_paths = []
    r1 = Pretty(f'Hello {os.environ['USERNAME']}, Enter The File Location Of Where The Scanned Certs Are Being Stored')
    panel = Panel(r1,title='Cert Scanner V.1.0',expand=False,subtitle='File Path:', subtitle_align="center") 
    

    print(Align.center(panel))
    file_path1 = Path(input())

    if not os.path.isdir(file_path1):
        while True:
            r2 = Pretty(f'The Given Folder Path Does NOT Exist, Please Try Again')
            panel = Panel(r2, expand=False, title='ERROR', title_align='center')
            print(Align.center(panel))
            file_path1 = input()
            if os.path.isdir(file_path1):
                break
            continue
    file_paths.append(file_path1)
        
    q1 = Pretty('Would You Like To Save This Folder Location For Next Time ?')
    panel = Panel(q1,expand=False,subtitle='Yes or No', subtitle_align="center")

    print(Align.center(panel))
    save_bool = input() 

    r2 = Pretty('Enter The File Path To The Folder Where Renamed Certs Will Be Stored')
    panel = Panel(r2, expand=False, subtitle_align='center', subtitle='This Should Be Somewhere On the Share Drive')
    
    
    print(Align.center(panel))
    file_path2 = Path(input())
    if not os.path.isdir(file_path2):
        while True:
            r2 = Pretty(f'The Given Folder Path Does NOT Exist, Please Try Again')
            panel = Panel(r2, expand=False, title='ERROR', title_align='center')
            print(Align.center(panel))
            file_path2 = input()
            if os.path.isdir(file_path2):
                break
            continue 

    file_paths.append(file_path2)
    

    if save_bool.lower() in ['yes', 'no', 'y', 'n']:
        save_bool = True
    else:
        save_bool = False

    return file_paths, save_bool


def checkConfig() -> bool | dict[str,str | bool]: 
    '''checks to see if the file exist if it does reads
    the file path from the file and returns it, if its
    the users first time using the program it returns False
    '''

    appDataLocal = str(os.getenv('LOCALAPPDATA'))
    dirPath = os.path.join(appDataLocal,'certScanner')
    filePath = os.path.join(appDataLocal,'certScanner','config.json')

    if os.path.isdir(dirPath):
        if os.path.isfile(filePath): 
            with open(filePath, 'r') as file:
                locations = json.load(file)
                if locations['firstTime'] == True:
                    return False
            if (os.path.isdir(locations['Scanned Certs'])
                and os.path.isdir(locations['Renamed Certs'])):
                config = locations
                return locations
    return False


def save_fp(file_paths: list[str]) -> dict[str, str | bool]:
    '''saves the given file path to The config if 
    the config dir does not exist it will make it.'''
    configStructure = {
            "Scanned Certs": str(file_paths[0]), 
            "Renamed Certs": str(file_paths[1]), 
            "firstTime": False 
            }


    appDataLocal = str(os.getenv('LOCALAPPDATA'))
    dirPath = os.path.join(appDataLocal, 'certScanner')
    if not os.path.isdir(dirPath):
        os.mkdir(dirPath)
    with open(fr'{dirPath}\config.json', 'w+') as file:
        json.dump(configStructure,file)
    return configStructure 
        

def startCertScan(config: dict[str, str | bool] | list[str]):
    images_array = []

    if isinstance(config, dict):
        scannedFiles: str = config['Scanned Certs'] # pyright: ignore[]
        renamedFiles: str = config['Renamed Certs'] # pyright: ignore[]
    else:
        scannedFiles: str = config[0]
        renamedFiles: str = config[1]

    for file in os.scandir(scannedFiles):
        if os.path.isdir(file.path):
            os.chdir(file.path)
            print(file.path)
        for file in os.scandir(file.path):
            images_array.append(file)

    if len(images_array) > 8:
        with ThreadPoolExecutor(max_workers=6) as exe:
            results = exe.map(scan,images_array)
            
        print(list(results))
    else:
        results = map(scan,images_array)
        print(list(results))
        



def scan(image: os.DirEntry):
    certNumber_rois = (112,2929,611,3195)

    with pymupdf.open(image) as pdf:
        page = pdf[0] 
        page.set_cropbox(pymupdf.Rect(certNumber_rois))
        pdf.save(config['Scanned Certs'])
        scanned_data = pytesseract.image_to_string(page, lang='eng')
        print(scanned_data)


    # while re.fullmatch(r'^3DEO-\d{3}$',scanned_data ):
        #     print('sacn')

    # WIP
    # print('running scan')
    # InstrumentID_rois = (179,809,551,954)
    #
    # with Image.open(Path(image)) as jpgImg: 
    #     # jpgImg.convert('RGB').save(str(image.name).replace('.jpg','.pdf'),"PDF") 
    #     certNumber_crop = jpgImg.crop(certNumber_rois)
    #     instrumentID_crop = jpgImg.crop(InstrumentID_rois)
    #     certNumber_scan = pytesseract.image_to_string(certNumber_crop, lang='eng')
    #     instrumentID_scan = pytesseract.image_to_string(instrumentID_crop, lang='eng')
    #     instrumentID_data = parseData(instrumentID_scan) 
    #     certNumber_data = parseData(certNumber_scan) 
    #     for file in os.scandir():
    #             mergeFiles(file, jpgImg, image, certNumber_data,instrumentID_data)
    #     renameFiles(image, f'3DEO-{instrumentID_data}'.__add__(f'_{certNumber_data}'))
    # return 
    #
    #
def renameFiles(original: os.DirEntry , new: str ):
    try:
        os.rename(original, f'{new}.jpg')
    except FileExistsError:
        print(f'')
         
        pass
    return 
     


def mergeFiles(top: os.DirEntry, bottom: Image.Image, bottomPath: os.DirEntry,
               certNumber: str, instrumentID: str):
    topPdfPath = str(top).replace('.jpg','.pdf')
    bottomPdfPath = str(bottomPath).replace('.jpg','.pdf')
    mergable = []
    mergable.append(topPdfPath)
    mergable.append(bottomPdfPath)
    topImg = Image.open(top) 
        # topImg.convert("RGB").save(f'{topImg}.pdf',"PDF")
    topImg.convert('RGB').save(topPdfPath, 'PDF')
    topImg.close()
     
    bottom.convert('RGB').save(bottomPdfPath,'PDF')
    bottom.close()

    with Image.open(topPdfPath) as topPdf ,Image.open(bottomPdfPath) as bottomPdf:
        merger = PdfWriter() 

        [merger.append(img) for img in mergable]
        merger.write(f'3DEO-{instrumentID}_{certNumber}.pdf')
        merger.close()

        
    # os.remove(top)
    # os.remove(bottomPath)
    return



def parseData(data: str):
    for letter in data:
        try:
            int(letter)
        except (TypeError, ValueError):
            data = data.replace(letter, '')
    if data.startswith('0'):
        data = '' + data[1:]
    return data

def afterScanCleanup():
    '''delete all files in the scanned certs directory
    since theyve been renamed and copied over to renamed directory'''
    return


def main():

    pytesseract.pytesseract.tesseract_cmd = r'C:\Users\jrogers\AppData\Local\Programs\Tesseract-OCR\tesseract'
    fp = checkConfig() #check to see if config exist
    if isinstance(fp,dict):
        startCertScan(fp) #if it does read the paths from conf and run the scan
    else:
        file_path, save = start() # if the config doesnt exist run the startup
        if save:
            saved_dict = save_fp(file_path) # make the config with obtained info
            startCertScan(saved_dict)# finally when all checks are good scan the certs
        else:
            startCertScan(file_path)
    return 

#C:\Users\jrogers\Desktop
if __name__ == "__main__":
    main()


