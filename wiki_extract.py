import pandas as pd
import requests
import sys
import re
from bs4 import BeautifulSoup
import wikipedia
import logging


class WikiExtact:
    def __init__(self):
        self.url = "https://en.wikipedia.org/wiki/"
        # Wikipedia has different types of 'infobox'
        # The for loop below checks what type of infobox the company page has
        # to make sure the variable 'infobox' exists to use in the rest of the code
        self.infobox_types = [
            "infobox vcard",
            "infobox hproduct",
            "infobox company",
            "infobox brewery",
        ]
        # This list contains all different types of information an infobox can contain
        self.info_list = [
            "Type of business",
            "Industry",
            "Type",
            "Founded",
            "Founder(s)",
            "Founders",
            "Founder",
            "Headquarters",
            "Area served",
            "Number of employees",
            "Employees",
            "Products",
            "Product type",
            "Owner",
            "Produced by",
            "Country",
            "Number of locations",
            "Revenue",
        ]

    def get_info(self, company: str) -> dict:
        """
        This function extracts information from company wikipedia
        pages.
        """
        url_search = self.url + company
        print(url_search)
        # Request URL for company page (changes with input)
        res = requests.get(url_search)
        # Create soup and store in variable
        soup = BeautifulSoup(res.content, "html.parser")

        self.data_dict = dict()  # Store data
        self.data_dict["Company"] = company

        for infobox_type in self.infobox_types:
            infobox = soup.find("table", {"class": infobox_type})
            if infobox:
                break

        if not infobox:
            print(f"No matching infobox found for {company}")
            return None

        # Store the items in the infobox found in a list
        # Note: information differs per company
        infobox_info = infobox.find_all("tr")

        # This function checks if 'Founders' is in the information
        # If yes, then Founder will be removed from the list
        if "Founder(s)" in str(infobox_info):
            self.info_list.remove("Founders")
            self.info_list.remove("Founder")

        if "Founders" in str(infobox_info):
            self.info_list.remove("Founder")

        if "Type of business" in str(infobox_info):
            self.info_list.remove("Type")

        # Creating the summary of the company and adding it to the dictionairy
        try:
            company_page = wikipedia.page(company)
            company_summary = company_page.summary
            self.data_dict["Summary"] = company_summary.replace("\n", "").strip()

        except Exception as e:
            # Handle the specific exception and provide an appropriate error message
            logging.error(f"Error retrieving summary for {company}: {str(e)}")
            self.data_dict["Summary"] = None

        # Loop that checks if the different types of information are present on the wikipedia page
        # When found the prefix (key) is removed, leaving us with the value
        for index, info_row in enumerate(infobox_info):
            for info in self.info_list:
                if info_row.text.startswith(
                    info
                ):  # Check for startswith, not only contains
                    info_value = info_row.text.removeprefix(info)

                    # Handle specific cases for extracting information
                    if info == "Number of employees" or info == 'Employees':
                        info = "Number of employees"
                        info_value = info_value.split()[0]
                        
                    if info == "Number of locations":
                        info_value = int(info_value.split()[0].replace(',', ''))

                    if info == "Type of business":
                        info = "Type"

                    if info == "Founders" or info == "Founder(s)":
                        info = "Founder(s)"
                        info_value = [
                            x.strip()
                            for x in re.split(r"(?<=[a-z])\n?(?=[A-Z])", info_value)
                        ]

                    if info == "Founder":
                        info = "Founder(s)"

                    if info == "Industry":
                        info_value = [
                            x.strip()
                            for x in re.split(r"(?<=[a-z])(?=[A-Z])|,", info_value)
                        ]
                        if len(info_value) == 1:
                            info_value = info_value[0]

                    if info == "Headquarters":
                        if "U.S." in info_value:
                            info_value = "U.S."
                        else:
                            info_value = re.split(",", info_value)[-1].strip()               
                    
                    if info == 'Products' and company == 'Apple Inc.':
                        if isinstance(info_value, str):
                            info_value = re.split('\n', info_value)
                            info_value = [x for x in info_value if x != '']

                    if info == "Products":
                        if isinstance(info_value, str):
                            info_value = re.split(
                                "\n|,|(?<=[a-z])(?=[A-Z])", info_value
                            )
                            info_value = [x for x in info_value if x != ""]

                        if len(info_value) == 1:
                            info_value = info_value[0]

                    if info == "Product type":
                        info = "Products"
                        info_value = [x for x in re.split(",", info_value)]

                    if info == "Type":
                        info_value = info_value.split()[0]

                    if info == 'Revenue':
                        match = re.search(r'([\d.,]+)\s?(million|billion|trillion)?', info_value)
                        if match:
                            amount = match.group(1).replace(',', '')
                            scale = match.group(2)

                            scales = {'million': 1e6, 'billion': 1e9, 'trillion': 1e12}
                            scale_factor = scales.get(scale, 1)

                            info_value = int(float(amount) * scale_factor)
                        else:
                            info_value = None

                    if info == "Founded":
                        # Match a word boundary followed by 4 digits and another word boundary
                        year_pattern = re.compile(r"\b\d{4}\b")

                        # Search for the first occurrence of the pattern in the string
                        year_match = year_pattern.search(info_value)

                        # Extract the matched string and convert it to an integer
                        if year_match:
                            info_value = int(year_match.group())

                    # After everything checks out, the new key:value pair is added to the dictionairy
                    self.data_dict[info] = info_value

        return self.data_dict
    

    def append_to_df(self):
        
        dataframe = pd.DataFrame()
        
        # Get the keys and values from the dictionary
        keys = list(self.data_dict.keys())
        values = list(self.data_dict.values()) 

        # Compute the number of rows needed based on the values
        num_rows = 1
        for key, value in zip(keys, values):
            if isinstance(value, list) and key != 'Founder(s)':
                num_rows *= len(value)   

        print(num_rows)

        # Create a list to hold the dictionaries
        rows = []

            # Iterate over the number of rows
        for i in range(num_rows):
            # Create a dictionary for the row
            row_dict = {}
            
            # Iterate over the keys and values
            for j in range(len(keys)):
                value = values[j]
                
                # Handle single values
                if not isinstance(value, list):
                    row_dict[keys[j]] = value
                # Handle list values
                else:
                    if keys[j] == 'Founder(s)':
                        row_dict[keys[j]] = value
                    
                    else:
                        num_values = len(value)
                        index = (i // (num_rows // num_values)) % num_values
                        row_dict[keys[j]] = value[index]
            
            rows.append(row_dict)
        
        # Append the list of dictionaries to the DataFrame
        dataframe = dataframe.append(rows, ignore_index=True)
        
        return dataframe