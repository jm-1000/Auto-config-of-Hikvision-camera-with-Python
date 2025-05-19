import argparse
from time import sleep
from json import load

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import \
    InvalidElementStateException as InvalidElem
from selenium.webdriver.remote.webelement import WebElement

from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support.expected_conditions import (
        presence_of_all_elements_located as presence_all_elems,
        element_to_be_clickable as elem_clickable
    )


ARGS = {
    "-i": "Nouvelle IP de la caméra",
    "-I": "Actuelle IP de la caméra",
    "-m": "Masque du réseau",
    "-g": "IP de la passerelle",
    "-n": "Nom de la caméra",
    "-p": "Mot de passe"
}

CAM_URL = "http://192.168.1.64"

TIMER = 1



class CamConfig():
    USER = "admin"
    FILE = "./cam_config.json"
    RETRY_TAB = 3

    def __init__(self, url:str, timer:int=2):
        self.url = url
        self.timer = timer
        self.data = {}
        self.config_data = {}
        self.args_dict = {}
        self.redo_tab = {
            "cur_tab": "", "try_cur_tab": self.RETRY_TAB, 
            "prev_tab": [], "try_prev_tab": self.RETRY_TAB,
            "tab_done": []
        }
        self.errors = {
            "error_tab": [], 
            "occured": False
        }
        self.body = lambda: self.driver.find_element(By.TAG_NAME, "body")
        self.wait_elem = lambda _xpath: WebDriverWait(self.driver, 3).until(
            presence_all_elems((By.XPATH, _xpath)))
        self.get_params()
        self.read_config_file()
        self.driver = webdriver.Firefox()
   

    def click_tab(self, elem_txt:str):
        for tag in ["span", "a", "p"]:
            try:
                _elem = WebDriverWait(self.body(), 0.5).until(
                        elem_clickable((By.XPATH, f".//{tag}[text()='{elem_txt}']")))
                if _elem: _elem.click();  return True
            except: pass
        return False
    

    def do_inputs(self, inputs:list, value:list):
        _type_attr = inputs[0].get_attribute("type")
        try:
            if inputs[0].tag_name == "select": 
                for i in range(len(value)): 
                    Select(inputs[i]).select_by_visible_text(value[i])

            elif _type_attr == "checkbox" and value[0] :
                try:
                    if not inputs[0].is_selected(): inputs[0].click()
                except: inputs[0].find_element(By.XPATH, "./..").click()

            elif _type_attr == "radio" :
                for item in value:
                    try: 
                        if not inputs[item].is_selected(): inputs[item].click()
                    except: inputs[item].find_element(By.XPATH, "./..").click()

            elif _type_attr == "text" or _type_attr == "password": 
                for i in range(len(value)):
                    if inputs[i].get_attribute("unselectable") == "off":
                        if value[i] == inputs[i].get_attribute('value'): continue
                        try: inputs[i].click()
                        except: inputs[i].find_element(By.XPATH, "./..").click()
                        for li_elem in self.wait_elem("//ul//li[span]"): 
                            if value[i] == li_elem.text.strip(): li_elem.click(); break
                    
                    else:
                        if value[i] == inputs[i].get_attribute('value'): continue
                        inputs[i].send_keys(Keys.CONTROL + "a")
                        inputs[i].send_keys(Keys.DELETE)
                        inputs[i].send_keys(value[i])
        except InvalidElem: pass
        except Exception as e : raise(e)


    def do_login(self):
        try: _inputs = self.driver.find_element(By.TAG_NAME, 'form').find_elements(
                By.TAG_NAME, 'input')
        except: _inputs = self.driver.find_elements(By.TAG_NAME, 'input')
        _last_passwd_input = _inputs[0]
        _inputs.reverse()
        for _input in _inputs:
            if _input.is_displayed():
                if _input.get_attribute('type') == 'password':
                    _input.send_keys(self.config_data['Password'])
                elif _last_passwd_input.get_attribute('type') == 'password' : 
                    try: _input.send_keys(self.USER)
                    except: pass
                _last_passwd_input = _input
        self.save_conf()

    
    def do_page(self):
        _span_done = []
        _last_num_input = 0
        while True:
            _inputs = self.find_input_elems()
            if _last_num_input == len(_inputs): break
            _last_num_input = len(_inputs)
            for span in self.config_data.keys():
                if self.config_data[span] and \
                    span in _inputs.keys() and span not in _span_done: 
                    try: self.do_inputs(_inputs[span], self.config_data[span])
                    except: 
                        print(f"\nErreur : champs '{span}' non rempli.")
                        self.errors['occured'] = True
                    _span_done.append(span)


    def do_security_question(self):
        try: 
            try: self.driver.find_element(By.XPATH,"//button[text()='OK']")
            except: 
                _xpath = "//button[span[text()='Not Set Temporarily']]"
                self.driver.find_element(By.XPATH, _xpath)
            sleep(self.timer)
            self.do_page(); self.save_conf()
            sleep(self.timer)
            self.driver.get(self.url)
            sleep(self.timer) 
            if self.get_version == 1: self.set_lang()
            self.do_login()
            sleep(self.timer)
        except: pass


    def do_tab(self, tabs:list):
        if self.redo_tab["cur_tab"] != tabs[0]: 
            self.redo_tab["cur_tab"] = tabs[0]
            self.redo_tab["try_cur_tab"] = self.RETRY_TAB

        if self.click_tab(tabs[0]):
            if self.redo_tab["prev_tab"] != tabs:
                self.redo_tab["prev_tab"] = tabs
                self.redo_tab["try_prev_tab"] = self.RETRY_TAB
            
            if tabs[0] in ["Image", "Configuration"]: sleep(self.timer)
            if len(tabs) > 1:
                for tab in tabs[1]: self.do_tab(tab)
            else: 
                if tabs[0] in self.redo_tab["tab_done"]: return None
                self.redo_tab["tab_done"].append(tabs[0])
                sleep(self.timer) 
                print("Remplissant la section :", tabs[0])
                self.do_page()
                if tabs[0] in ["TCP/IP", "Basic Settings"]:
                    try: 
                        self.save_conf()
                        if self.web_version == 1:
                            self.wait_elem(
                                '//div[.//span[normalize-space()="Restart the device?"]]'
                                '//button[span[normalize-space()="Cancel"]]'
                                )[0].click()
                        else: self.wait_elem('//button[text()="Cancel"]')[0].click()
                    except: pass
                self.save_conf()
                try:
                    if self.web_version == 1:
                        self.wait_elem("//div[p[normalize-space()='Saved.']]")
                    else:
                        self.wait_elem("//div[text()='Save succeeded.']")
                except: 
                    print("Erreur : Impossible de sauvegarder la section :", tabs[0])  
                    self.errors['occured'] = True      

        else:
            if self.redo_tab["try_cur_tab"] > 1:
                self.redo_tab["try_cur_tab"] -= 1
                self.do_tab(tabs)
            elif self.redo_tab["try_prev_tab"] > 1:
                self.redo_tab["try_prev_tab"] -= 1 
                try: self.do_tab(self.redo_tab["prev_tab"])
                except: pass
            else:
                if tabs[0] not in self.errors["error_tab"]:
                    print(f"Erreur: section '{tabs[0]}' non selectionnée")
                self.errors['error_tab'].append(tabs[0])
                self.errors['occured'] = True

        
    def find_input_elems(self):
        if self.web_version == 1:
            return CamWebInterface1().find_input_elems(self.driver)
        elif self.web_version == 2:
            return CamWebInterface2().find_input_elems(self.driver)


    def get_version(self):
        try:
            try: 
                self.body().find_element(By.XPATH, CamWebInterface1.XPATH_LANG[0])
                return 1 
            except: 
                self.body().find_element(By.XPATH, CamWebInterface2.XPATH_LANG[0])
                return 2
        except: raise("Version d'interface web non determinee")


    def get_params(self):
        _parser = argparse.ArgumentParser()
        for k in ARGS.keys():
            _parser.add_argument(k, type=str, required=True if k != '-I' else False, help=ARGS[k])
        self.args_dict = vars(_parser.parse_args())
        if self.args_dict['I']: self.url = "http://" + self.args_dict['I']


    def main(self):
        print("Connexion à l'interface web...\n")
        self.driver.get(self.url)
        sleep(self.timer)
        
        self.web_version = self.get_version()
        self.config_data = self.data[str(self.web_version)]["config"]
        for key, value in self.data[str(self.web_version)]["params"].items():
            self.config_data[key] = [self.args_dict[value]]

        if self.get_version == 1: self.set_lang()    
        self.do_login()
        sleep(self.timer)
        self.do_security_question()
        self.do_tab(self.data[str(self.web_version)]["tabs"])
        
        _txt = '\nVérifier les configurations et puis faire la mise à jour!'
        print(_txt)
        if self.errors['occured']:
            _txt = "Sections avec des erreurs! Allez voir la console."
        self.driver.execute_script("alert(arguments[0])", _txt)
        input("")
        
        self.driver.quit()


    def save_conf(self):
        for _btn in self.driver.find_elements(By.XPATH, f'//button'):
            _btn_txt = _btn.get_attribute("innerHTML")
            for txt in ["Save", "OK", "Login", "Log In", "Activation"]: 
                if _btn.is_displayed() and txt in _btn_txt : _btn.click(); return None
    

    def set_lang(self, lang:str="English"):
        if self.web_version == 1:
            _xpaths = CamWebInterface1.XPATH_LANG
        elif self.web_version == 2:
            _xpaths = CamWebInterface2.XPATH_LANG
        try:
            _btn = self.driver.find_element(By.XPATH, _xpaths[0])
            if _btn.get_attribute('title') != lang: 
                _btn.find_element(By.XPATH, './..').click()
                self.wait_elem(_xpaths[1].replace('lang', lang))[0].click()
                sleep(self.timer)
        except: pass


    def read_config_file(self):
        try:
            with open(self.FILE, 'r') as file: self.data = load(file)
        except: raise("Impossible de lire le fichier JSON.")
 



class CamWebInterface1():
    XPATH_LANG = [
        ".//input[normalize-space(@title)!='']",
        "//ul[li]/li[span[normalize-space()='lang']]"
    ]

    def find_input_elems(self, driver:webdriver):
        _elems = {}
        for input in driver.find_elements(By.TAG_NAME, "input"):
            try:
                _span = self.find_text_elem(input)
                if _span:
                    try:
                        if _span.text in _elems.keys() :
                            _elems[_span.text.strip()].append(input)
                        else: 
                            _elems[_span.text.strip()] = [input]
                    except: pass
            except Exception as e: raise(e)
        return _elems
    

    def find_text_elem(self, ref_elem:WebElement, depth:int=5):
        i = 1
        _xpath = "./..//span[normalize-space() != '']"
        try: right_span = ref_elem.find_element(By.XPATH, _xpath)
        except: right_span = None
        while i < depth:
            i+=1
            _xpath = f"ancestor::div[{i}]//preceding-sibling::" \
                "span[normalize-space() != '']"
            for _elem in ref_elem.find_elements(By.XPATH, _xpath):
                if (right_span and right_span.text == _elem.text) or \
                _elem.find_element(By.XPATH, './..').tag_name == 'span': continue
                try: _elem.find_element(By.XPATH, './/*')
                except: 
                    try:
                        if _elem.text.strip() != "": return _elem
                    except: pass
            
        


class CamWebInterface2():
    XPATH_LANG = [
        ".//div[span[normalize-space()!='' and normalize-space()=@title]]/span", 
        "//div[div[normalize-space()='lang']]/div[normalize-space()='lang']"
    ]

    def find_input_elems(self, driver:webdriver):
        _elems = {}
        for input in [
            *driver.find_elements(By.TAG_NAME, "select"), 
            *driver.find_elements(By.TAG_NAME, "input")]:
            try:
                if input.is_displayed():
                    _span = self.find_text_elem(input, "./preceding-sibling::span")
                    _label = self.find_text_elem(input, ".//label", 2)
                    if not _span and not _label : continue
                    try:
                        if _label and not _span: 
                            _elems[_label.text.strip()] = [input]
                        if _span.text in _elems.keys() :
                            _elems[_span.text.strip()].append(input)
                        else: 
                            _elems[_span.text.strip()] = [input]
                    except: pass
            except Exception as e: raise(e)
        return _elems
    

    def find_text_elem(self, ref_elem:WebElement, xpath: str, depth:int=4):
        while xpath.count("..") < depth:
            for _elem in ref_elem.find_elements(By.XPATH, xpath):
                try: 
                    _elem.find_element(By.XPATH, './/*')
                except: 
                    try:
                        if _elem.text.strip() != "": return _elem
                    except: return None
            xpath = "./." + xpath



cam = CamConfig(CAM_URL, TIMER)
try: 
    cam.main() 
except Exception as e: 
    cam.driver.quit()
    print(e) 