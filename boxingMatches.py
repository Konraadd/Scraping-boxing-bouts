# -*- coding: utf-8 -*-
import scrapy
import re
import csv
import time

class boxingMatches(scrapy.Spider):
    name = 'boxingMatches'
    allowed_domains = ['boxrec.com']
    start_urls = ['http://boxrec.com/en/login']

    def parse(self, response):
        print("Logging in to: " + response.url)
        # log in to boxrec.com to bypass requests limit
        return scrapy.FormRequest('https://boxrec.com/en/login',
                                  formdata={'_username': 'username', '_password': 'password'},
                                  callback=self.after_login
        )

    def after_login(self, response):
        # check if login worked, if so start extracting data about boxers from ratings subpage
        if "authentication failed" in str(response.body):
            self.logger.error("Login failed")
            print('Login failed')
            return
        yield response.follow("https://boxrec.com/en/ratings?ipM%5Bcountry%5D=&ipM%5Bdivision%5D=&ipM%5Bsex%5D=M&ipM%5"
                              "Bstance%5D=&ipM%5Bstatus%5D=&r_go==", self.parse_pages)

    def parse_pages(self, response):
        # wait for one second. Attempt to avoid getting HTTP 429 (too many requests) error
        time.sleep(1)
        print("Parsing authenticated url " + response.url)
        # get boxers ids and 'visit' their pages
        boxers = response.xpath('//a[contains(@href, "/en/proboxer/")]').extract()
        for boxer in boxers:
            time.sleep(1)
            # process boxers sites with 'parse_boxer' function
            yield response.follow('https://boxrec.com/en/proboxer' + re.search("/\d+", boxer).group(), self.parse_boxer)
        # get information from 'next page' button
        next_page = response.xpath('//div[contains(@class, "tableInfoBottom")]/div/div[last()]/a').extract()
        try:
            next_page = re.search("href.+onclick", str(next_page)).group()[6:-9]
        except AttributeError:
            return

        # delete 'amp;' characters
        next_page = next_page.replace("amp;", "")
        # go to the next page
        yield response.follow("https://boxrec.com/en/" + next_page, self.parse_pages)

    def parse_boxer(self, response):
        bouts = response.xpath('//div/a[contains(@href, "/en/event")]').extract()
        # only get every second href link, starting from second (index '1')
        bouts = bouts[1::2]
        bouts = [re.search('/en/event/\d+/\d+', b).group() for b in bouts]
        for bout in bouts:
            time.sleep(1)
            yield response.follow('https://boxrec.com' + bout, self.parse_bout)

    def parse_bout(self, response):
        result = response.xpath('//span[contains(@class, "textWon")]').extract()
        if result.__contains__('won'):
            result_of_bout = 1
        else:
            result_of_bout = 0

        data = response.xpath('//table[contains(@class, "responseLessDataTable")]/tr/td[contains(@style,'
                                ' "text-align:right;")]').extract()
        opponent_data = response.xpath('//table[contains(@class, "responseLessDataTable")]/tr/td[contains(@style,'
                                ' "text-align:left;")]').extract()
        # getting values from data
        points_before = data[2]
        points_after = data[3]
        age = data[4]
        stance = data[5]
        height = data[6]
        reach = data[7]
        opponent_points_before = opponent_data[2]
        opponent_points_after = opponent_data[3]
        opponent_age = opponent_data[4]
        opponent_stance = opponent_data[5]
        opponent_height = opponent_data[6]
        opponent_reach = opponent_data[7]
        # cleaning data
        # It won't parse if any of the statistics are missing, except for stance
        try:
            stance = re.search('>.+<', stance).group()[1:-1]
            opponent_stance = re.search('>.+<', opponent_stance).group()[1:-1]
        except AttributeError:
            print('No stance avaiable for a boxer. Carrying on.')
        try:
            points_before = re.search('\d+\.*\d*', points_before).group()
            points_after = re.search('\d+\.*\d*', points_after).group()
            age = re.search('\d+', age).group()
            height = re.search('/\d+c', height).group()[1:-1].lstrip()
            reach = re.search('/\d+c', reach).group()[1:-1].lstrip()
            opponent_points_before = re.search('\d+\.*\d*', opponent_points_before).group()
            opponent_points_after = re.search('\d+\.*\d*', opponent_points_after).group()
            opponent_age = re.search('\d+', opponent_age).group()
            opponent_height = re.search('/\d+c', opponent_height).group()[1:-1].lstrip()
            opponent_reach = re.search('/\d+c', opponent_reach).group()[1:-1].lstrip()
        except AttributeError:
            print('Some attributes are missing. Aborting')
            return

        print(result_of_bout)
        print(points_before)
        print(points_after)
        print(age)
        print(stance)
        print(height)
        print(reach)
        print('=========')
        print(opponent_points_before)
        print(opponent_points_after)
        print(opponent_age)
        print(opponent_stance)
        print(opponent_height)
        print(opponent_reach)

        with open('boxing_bouts.tsv', 'a+') as file:
            writer = csv.writer(file, delimiter='\t')
            writer.writerow([points_before, points_after, age, stance, height, reach, opponent_points_before,
                             opponent_points_after, opponent_stance, opponent_height, opponent_reach, result_of_bout])
