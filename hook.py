#!/usr/bin/env python3

import configparser
import sys
import os
import logging
import time

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from bs4 import BeautifulSoup
from tld import get_tld
import dns.exception
import dns.resolver

class DNSChallengeHook:
    """Manages DNS challenges for the ACME Protocol."""

    def __init__(self, config_path="default.ini"):
        """Reads in config from config_path (default: default.ini)
        and sets configuration accordingly."""

        # Change working dir to script dir
        abspath = os.path.abspath(__file__)
        dir_name = os.path.dirname(abspath)
        os.chdir(dir_name)

        if os.path.isfile(config_path):
            config = configparser.ConfigParser()
            config.read(config_path)
            self.username   = config["Login"]["Username"]
            self.password   = config["Login"]["Password"]
        else:
            print("Please provide a configuration file named '" + config_path + "'.")
            exit(1)

    def cli(self, args):
        if (len(args) > 0 and args[0] == "deploy_challenge"):
            self.domain = args[1]
            self.token = args[2]
            self.deploy_challenge()
        elif (len(args) > 0 and args[1] == "clean_challenge"):
            self.clean_challenge()
            self.domain = args[1]
        else:
            print("This hook only works with 'deploy_challenge' and 'clean_challenge'")
            exit(1)

    def deploy_challenge(self, args):
        """Deploys the challenge token as a TXT record."""
        print("deploy_challenge: Registering new TXT record...")

        driver = webdriver.Firefox()
        driver.get("https://controlpanel.register.it/index.html?chglng=eng")

        # login
        self._wait_for_element_with_id(driver, "hd_loginbox")
        driver.find_element_by_id("hd_loginbox").click()
        driver.find_element_by_name("userName").send_keys(self.username)
        driver.find_element_by_name("password").send_keys(self.password)
        driver.find_element_by_name("password").send_keys(Keys.RETURN)
        self._wait_for_element_with_id(driver, "nav")

        base_url = "https://controlpanel.register.it/"


        driver.get(base_url + "firstLevel/view.html?domain=" + get_tld("http://" + self.domain))
        self._wait_for_element_with_id(driver, "webapp_domain")
        driver.get(base_url + "domains/dnsAdvanced.html")
        self._wait_for_element_with_id(driver, "backToApps")
        driver.find_element_by_class_name("add").click()
        dns_soup = BeautifulSoup(driver.page_source, "html.parser")
        dns_entries = len(dns_soup.find("table", class_="dinamicList")
                .find_all("tr", class_="rMain"))
        new_dns_entry = dns_entries - 1 # zero based indexing
        driver.find_element_by_name("recordName_"
                + str(new_dns_entry)).send_keys(self.domain)
        driver.find_element_by_name("recordTTL_"
                + str(new_dns_entry)).send_keys("900")
        select = Select(driver.find_element_by_name("recordType_"
                + str(new_dns_entry)))
        select.select_by_value("TXT")
        driver.find_element_by_name("recordValue_"
                + str(new_dns_entry)).send_keys(self.token)
        driver.find_element_by_class_name("submit").click()
        driver.find_element_by_xpath("//*[contains(text(), 'Continue')]").click()
        driver.close()
        print("TXT record registered...")
        print("Checking if DNS has propagated...")
        while(self._has_dns_propagated(self.domain, token) == False):
            print("DNS not propagated, waiting 30s...")
            time.sleep(30)


    def _wait_for_element_with_id(self, driver, element_id):
        """Explicitly waits for an element."""
        WebDriverWait(driver, timeout=10).until(
            lambda b: b.find_element_by_id(element_id)
        )

    def _has_dns_propagated(self):
        """Checks if the TXT record has propagated."""
        txt_records = []
        try:
            dns_response = dns.resolver.query(self.domain, 'TXT')
            for rdata in dns_response:
                for txt_record in rdata.strings:
                    txt_records.append(txt_record)
        except dns.exception.DNSException as error:
            return False

        for txt_record in txt_records:
            if txt_record == self.token:
                return True

        return False


if __name__ == "__main__":
    hook = DNSChallengeHook()
    hook.cli(sys.argv[1:])
