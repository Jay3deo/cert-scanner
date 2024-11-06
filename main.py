import functools
import img2pdf
from os.path import isdir
import re
from subprocess import IDLE_PRIORITY_CLASS
from typing import Match, final
from PIL.ImageFile import ImageFile
import pymupdf
from pypdf import PdfWriter
from pathlib import Path
import json
import pypdf
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

        print(results)

def scanPageNumber(image: os.DirEntry) -> int:

    print('running scan')
    pageNumber_rois = (2160,2958,2466,3208)
    pageNumber_pattern = 'Page [1-2] of [1-2]'    
    with Image.open(Path(image)) as jpgImg: 
        pageNumber_crop = jpgImg.crop(pageNumber_rois)
        pageNumber_scan = pytesseract.image_to_string(pageNumber_crop, lang='eng')
        match = re.search(pageNumber_pattern,pageNumber_scan)
        if match:
            
            pageNumber_data = parsePageNumber(pageNumber_scan) 
            if pageNumber_data == '11' or pageNumber_data == '12': #if the page if pg 1 of 1 or pg 1 of 2 we have the front page
                return int(pageNumber_data)
            
            return int(pageNumber_data)# else page 2 of 2 is the back page
        else:
            matchRetry = rescan(jpgImg,pageNumber_rois,pageNumber_pattern)
            if matchRetry:

                pageNumber_data = parsePageNumber(pageNumber_scan) 
                if pageNumber_data == '11' or pageNumber_data == '12': #if the page if pg 1 of 1 or pg 1 of 2 we have the front page
                    return int(pageNumber_data)
                
                return int(pageNumber_data)#
            return 0


def scanCertNum_and_id(imagePath_and_pageNum: tuple[os.DirEntry,bool]):
    cnf: list[tuple[os.DirEntry,str | None]] = []
    imagePath , pageNum= imagePath_and_pageNum

    certNum_roi = (58,2900,538,3220)
    certNum_pattern = r"Cert Number[: ]?\s?(\d+})"
    id_roi = (58,666,708,1122) 
    id_pattern = r'3DEO-\d{1,3}'

    if pageNum == 22:
        with Image.open(imagePath) as file:
            certNum_crop = file.crop(certNum_roi)
            certNum_data = pytesseract.image_to_string(certNum_crop)
            certNumber = parseDataCertNumber(certNum_data)
            if certNumber:
                renameFiles(imagePath,certNumber)
                for cert in os.listdir(os.path.dirname(imagePath)):
                    if certNumber in cert:
                        print(f'FOUND THE MATCH: {cert}, {certNumber} ')
                        mergeFiles(Path(cert),file,certNumber )
                        
    else:
        with Image.open(imagePath) as file:
            id_crop = file.crop(id_roi)
            certNum_crop = file.crop(certNum_roi)
            certNum_data = pytesseract.image_to_string(certNum_crop)
            id_data = pytesseract.image_to_string(id_crop)
            instrumentID = parseDataInstrumentID(id_data)
            certNumber = parseDataCertNumber(certNum_data)

            if certNumber == None:
                matchRetry = rescan(file,certNum_roi,certNum_pattern)
                if matchRetry:
                    certNumber = matchRetry
                else:
                    print(f'no match for {imagePath}', certNum_data)
                    print(f'{imagePath.name}')
                    cnf.append(imagePath.name)
                    return

            if instrumentID == None:
                matchRetry = rescan(file, id_roi, id_pattern)
                if matchRetry:
                    instrumentID = matchRetry
                else:
                    print(f'no match for {imagePath}', id_data)
                    print(f'Could not read: {imagePath.name}')
                    cnf.append(imagePath.name)
                    return
            renameFiles(imagePath,f'{instrumentID}_{certNumber}')



def rescan(file: ImageFile, roi, pattern: str) -> str | bool:
    print(f'rescanning {file}')
    adding = True 
    subtracting = False
    n=100
    while True:
        print(n)
        newRoi = tuple(x + n for x in roi)
        newCrop = file.crop(newRoi)
        newData = pytesseract.image_to_string(newCrop)
        match = re.search(pattern, newData)
        if adding:
            if n > 800:
                adding = False
                subtracting = True
                continue
        if n == 0:
            print(newData)
            return False
        if adding:
            if not match:
                n += 50
                continue
        if subtracting:
            if not match:
                n -=50
                continue
            else: 
                break
    print(match.group())
    return match.group()



        
def renameFiles(original: os.DirEntry , new: str ):
    os.rename(original, f'{new}.jpg')
    return f'{new}.jpg'
         

def mergeFiles(top: Path, bottom: ImageFile, certNumber: str):
    converted_top_name = str(top).replace('.jpg','.pdf')
    merger = pypdf.PdfWriter()
    with Image.open(top) as topFile:
        topFile.save(top.name.replace('.jpg','.pdf'), "PDF")
    bottom.save(certNumber + '.pdf', "PDF")
    merge = [converted_top_name,certNumber + '.pdf']
    for file in merge:
        merger.append(file)

    merger.write(top.name.replace('.jpg','.pdf'))
    merger.close()
    os.remove(certNumber + '.pdf')
    os.remove(top)
     


def parseDataInstrumentID(data: str) -> str | None:
    id_pattern = r'3DEO-\d{1,3}'
    bad_id_pattern = r'3DE0-\d{1,3}'
    match = re.search(id_pattern, data)
    if match:
        return match.group()
    else:
        matchRetry = re.search(bad_id_pattern, data)
        if matchRetry:
            return matchRetry.group().replace('3DE0', '3DEO')
        return None
    # for letter in data:
    #     try:
    #         int(letter)
    #     except (TypeError, ValueError):
    #         data = data.replace(letter, '')
    # if (data.startswith('3') or data.startswith('0')) and len(data) == 4:
    #     data = '' + data[1:]
    # return data

def parseDataCertNumber(data: str):
    certNum_pattern = r"Cert Number[: ]?\s?(\d+)"
    match = re.search(certNum_pattern, data)
    if match:
        data = match.group()
    else:
        return None
    for letter in data:
        try:
            int(letter)
        except (TypeError, ValueError):
            data = data.replace(letter, '')
    return data


def parsePageNumber(data: str):
    for letter in data:
        try:
            int(letter)
        except (TypeError, ValueError):
            data = data.replace(letter, '')
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


