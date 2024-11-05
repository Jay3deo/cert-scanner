import functools
from os.path import isdir
import re
from typing import Match, final
from PIL.ImageFile import ImageFile
import pymupdf
from pypdf import PdfWriter
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
            results = list(exe.map(scanPageNumber,images_array))
    else:
        results = list(map(scanPageNumber,images_array))
    
    setup = list(zip(images_array,results))
    finalSetup = []
    for i in setup:
        if i[1] == 22:
            finalSetup.append(i)
        elif i[1] == 11:
            finalSetup.insert(0,i)
        else:
            if len(finalSetup) == 0:
                finalSetup.append(i)
                continue
            for idx,l in enumerate(finalSetup):
                if l[1] == 12:
                    finalSetup.insert(idx,i)
                    break
                elif l[1] == 22:
                    finalSetup.insert(idx-1,i)
                    break
                



    z = [functools.partial(scanCertNum_and_id, imagePath_and_pageNum=x) for x in finalSetup]
    
    with ThreadPoolExecutor(max_workers=6) as exe:
        results = list(exe.map(lambda f: f(), z))

def scanPageNumber(image: os.DirEntry) -> int:

    print('running scan')
    pageNumber_rois = (2160,2958,2466,3208)
    
    with Image.open(Path(image)) as jpgImg: 
        pageNumber_crop = jpgImg.crop(pageNumber_rois)
        pageNumber_scan = pytesseract.image_to_string(pageNumber_crop, lang='eng')
        pageNumber_data = parseData(pageNumber_scan) 
        if pageNumber_data == '11' or pageNumber_data == '12': #if the page if pg 1 of 1 or pg 1 of 2 we have the front page
            return int(pageNumber_data)
        
        return int(pageNumber_data)# else page 2 of 2 is the back page
        


def scanCertNum_and_id(imagePath_and_pageNum: tuple[os.DirEntry,bool]):
    cnf: list[tuple[os.DirEntry,str | None]] = []
    imagePath , pageNum= imagePath_and_pageNum

    certNum_roi = (52,3040,526,3212)
    certNum_pattern = r'^\d{6}$'
    id_roi = (64,734,586,1058) 
    id_pattern = r'\d{1,3}'

    if pageNum == 22:
        print('just scan cer number and wait')
    else:
        with Image.open(imagePath) as file:
            id_crop = file.crop(id_roi)
            certNum_crop = file.crop(certNum_roi)
            cerNum_data = pytesseract.image_to_string(certNum_crop)
            id_data = pytesseract.image_to_string(id_crop)
            instrumentID = parseData(id_data)
            certNumber = parseData(cerNum_data)
            id_match = re.search(id_pattern, instrumentID.strip())
            certNum_match = re.fullmatch(certNum_pattern, certNumber.strip())
            if certNum_match == None:
                matchRetry = rescan(file,certNum_roi,certNum_pattern)
                if isinstance(matchRetry,re.Match):
                    certNumber = matchRetry.group()
            else:
                print(certNumber)

            if id_match == None:
                matchRetry = rescan(file, id_roi, id_pattern)
                if isinstance(matchRetry,re.Match):
                    print('<><><><><><><><><><><><><><><>')
                    print(matchRetry.group())
                    print('<><><><><><><><><><><><><><><>')
                else:
                    print(f'no match for {imagePath}')
            else:
                print(instrumentID)







def rescan(file: ImageFile, roi, pattern: str) -> re.Match | bool:
    
    n=50
    while True:
        newRoi = tuple(x + n for x in roi)
        newCrop = file.crop(newRoi)
        newData = pytesseract.image_to_string(newCrop)
        match = re.search(pattern, newData)
        if n > 400:
            print('no match could be found')
            return False 
        if not match:
            n += 50
            continue
        else: 
            break

    return match



        
def renameFiles(original: os.DirEntry , new: str ):
    try:
        os.rename(original, f'{new}.jpg')
    except FileExistsError:
        mergeFiles(
                top=Path(f'{new}.jpg'),
                bottom=original
                )
        pass
    return 
     

def mergeFiles(top: Path, bottom: os.DirEntry):
    with pymupdf.open(top) as topFile:
        topFile.convert_to_pdf()




def parseData(data: str):
    for letter in data:
        try:
            int(letter)
        except (TypeError, ValueError):
            data = data.replace(letter, '')
    if (data.startswith('3') or data.startswith('0')) and len(data) == 4:
        data = '' + data[1:]
    if len(data) == 5:
        data = '' + data[2:]
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


