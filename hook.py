#!/usr/bin/env python3

import configparser
import sys
import os
import logging
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions
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
            self.driver = webdriver.Firefox()
        else:
            print("Please provide a configuration file named '" + config_path + "'.")
            exit(1)

    def cli(self, args):
        if (len(args) > 0 and args[0] == "deploy_challenge"):
            self.domain = args[1]
            self.token = args[2]
            self._deploy_challenge()
        elif (len(args) > 0 and args[0] == "clean_challenge"):
            self.domain = args[1]
            self._clean_challenge()
        else:
            print("This hook only works with 'deploy_challenge' and 'clean_challenge'")
            self.driver.close()
            exit(1)

    def _login(self):
        """Logs the user in."""
        self.driver.get("https://controlpanel.register.it/index.html?chglng=eng")

        # login
        self._wait_for_element_with_id("userName")
        self.driver.find_element_by_id("userName").send_keys(self.username)
        self.driver.find_element_by_id("password").send_keys(self.password)
        self.driver.find_element_by_id("password").send_keys(Keys.RETURN)
        self._wait_for_element_with_id("nav")

    def _get_dns_form(self):
        """Navigates to the DNS configuration form."""
        base_url = "https://controlpanel.register.it/"
        self.driver.get(base_url + "firstLevel/view.html?domain=" + get_tld("http://" + self.domain))
        self._wait_for_element_with_id("webapp_domain")

        self.driver.get(base_url + "domains/dnsAdvanced.html")
        self._wait_for_element_with_id("backToApps")

    def _submit_dns_form(self):
        """Submits the changes on the DNS configuration form."""
        self.driver.find_element_by_class_name("submit").click()
        self._continue()

    def _continue(self):
        """Confirms the continue dialog."""
        self.driver.find_element_by_xpath("//a[contains(text(), 'Continue')]").click()

    def _deploy_challenge(self):
        """Deploys the challenge token as a TXT record."""
        print("deploy_challenge: Registering new TXT record...")

        self._login()

        self._get_dns_form()

        self.driver.find_element_by_class_name("add").click()
        dns_soup = BeautifulSoup(self.driver.page_source, "html.parser")
        dns_entries = len(dns_soup.find("table", class_="dinamicList")
                .find_all("tr", class_="rMain"))
        new_dns_entry = dns_entries - 1 # zero based indexing
        self.driver.find_element_by_name("recordName_"
                + str(new_dns_entry)).send_keys(self.domain)
        self.driver.find_element_by_name("recordTTL_"
                + str(new_dns_entry)).send_keys("900")
        select = Select(self.driver.find_element_by_name("recordType_"
                + str(new_dns_entry)))
        select.select_by_value("TXT")
        self.driver.find_element_by_name("recordValue_"
                + str(new_dns_entry)).send_keys(self.token)
        self._submit_dns_form()
        self.driver.close()
        print("TXT record registered...")
        print("Checking if DNS has propagated...")
        while(self._has_dns_propagated() == False):
            print("DNS not propagated, waiting 30s...")
            time.sleep(30)
        print("DNS propagated.")

    def _clean_challenge(self):
        """Deletes the challenge token."""
        print("clean_challenge: Deleting TXT record...")

        self._login()

        self._get_dns_form()
        css_class_name = self.domain.replace(".", "_")
        css_class_name += "_"
        (self.driver.find_element_by_class_name(css_class_name)
                .find_element_by_class_name("record_delete").click())
        self._continue()
        # Explicit wait after continue dialog
        time.sleep(1)
        self._submit_dns_form()
        self.driver.close()
        print("TXT record deleted.")

    def _wait_for_element_with_id(self, element_id):
        """Explicitly waits for an element."""
        WebDriverWait(self.driver, timeout=10).until(
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
