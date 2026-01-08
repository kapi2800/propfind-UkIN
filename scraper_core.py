"""
Property Scraper Core Module
Handles scraping of property buyer/seller data from eregistrationukgov.in
Uses AJAX for dropdown selections and full page POST for search.
"""

import requests
from bs4 import BeautifulSoup
import time
import re


class PropertyScraperCore:
    # URLs for different search types
    URLS = {
        "buyer": "https://online.eregistrationukgov.in/e_search/Buyer_Wise.aspx",
        "seller": "https://online.eregistrationukgov.in/e_search/Seller_Wise.aspx",
    }
    
    def __init__(self, search_type="buyer"):
        """Initialize scraper with search type ('buyer' or 'seller')."""
        self.search_type = search_type.lower()
        self.base_url = self.URLS.get(self.search_type, self.URLS["buyer"])
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        self.ajax_headers = {
            "X-Requested-With": "XMLHttpRequest",
            "X-MicrosoftAjax": "Delta=true",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }

    def get_hidden_fields(self, soup):
        """Extract ASP.NET hidden fields from the page."""
        data = {}
        for item in ["__VIEWSTATE", "__EVENTVALIDATION", "__VIEWSTATEGENERATOR"]:
            element = soup.find("input", {"id": item})
            if element:
                data[item] = element.get("value", "")
        return data

    def parse_ajax_response(self, text):
        """Parse ASP.NET AJAX UpdatePanel response format."""
        parts = text.split('|')
        result = {}
        i = 0
        while i < len(parts) - 3:
            try:
                length = int(parts[i])
                ptype = parts[i+1]
                pid = parts[i+2]
                content = parts[i+3]
                
                if ptype == 'hiddenField':
                    result[pid] = content
                elif ptype == 'updatePanel':
                    result[f"panel_{pid}"] = content
                    
                i += 4
            except (ValueError, IndexError):
                i += 1
        return result

    def parse_table(self, soup):
        """Parse the GridView2 table and extract records."""
        results = []
        table = soup.find("table", {"id": "GridView2"})
        if not table:
            return results

        rows = table.find_all("tr")
        if len(rows) < 2:
            return results
            
        # Skip header row (index 0)
        for row in rows[1:]:
            cols = row.find_all("td")
            
            # Skip pagination rows or other non-data rows
            if len(cols) < 10:
                continue
                
            try:
                record = {
                    "Village": cols[0].text.strip(),
                    "RegDate": cols[1].text.strip(),
                    "RegNo": cols[2].text.strip(),
                    "Area": cols[3].text.strip(),
                    "PropNo": cols[4].text.strip(),
                    "DeedType": cols[5].text.strip(),
                    "JildDetails": cols[6].text.strip(),
                    "Seller": cols[7].text.strip(),
                    "Buyer": cols[8].text.strip(),
                    "BuyerGender": cols[9].text.strip() if len(cols) > 9 else "",
                    "SRO": cols[10].text.strip() if len(cols) > 10 else "",
                    "Amount": cols[11].text.strip() if len(cols) > 11 else "",
                    "MarketValue": cols[12].text.strip() if len(cols) > 12 else ""
                }
                results.append(record)
            except (IndexError, AttributeError) as e:
                continue
                
        return results

    def check_pagination(self, soup, current_page):
        """Check if next page exists and return the page argument."""
        table = soup.find("table", {"id": "GridView2"})
        if not table:
            return None
            
        # Look for pagination links with Page$N pattern
        next_page = current_page + 1
        next_page_arg = f"Page${next_page}"
        
        # Find link containing next page reference
        next_link = table.find("a", href=lambda h: h and next_page_arg in h)
        
        if next_link:
            return next_page_arg
        return None

    def scrape_year(self, district_id, sro_id, year, name_pattern):
        """
        Generator that scrapes data for a single year.
        Yields status updates and data as it progresses.
        """
        results = []
        
        # CRITICAL: Fresh session per year
        with requests.Session() as s:
            s.headers.update(self.headers)
            
            yield {"status": "info", "message": f"Starting session for Year {year}..."}
            
            # 1. Initial GET
            try:
                r = s.get(self.base_url, timeout=60)
                soup = BeautifulSoup(r.content, "html.parser")
                vs = self.get_hidden_fields(soup)
            except Exception as e:
                yield {"status": "error", "message": f"Initial load failed: {str(e)}"}
                return

            time.sleep(2)

            # 2. Select District (AJAX postback)
            yield {"status": "info", "message": f"Selecting District {district_id}..."}
            
            s.headers.update(self.ajax_headers)
            
            payload = {
                "ctl00$ScriptManager1": "ctl00$MainContent$UpdatePanel1|ctl00$MainContent$ddl_dis",
                "__EVENTTARGET": "ctl00$MainContent$ddl_dis",
                "__EVENTARGUMENT": "",
                "__LASTFOCUS": "",
                "__VIEWSTATE": vs.get("__VIEWSTATE", ""),
                "__VIEWSTATEGENERATOR": vs.get("__VIEWSTATEGENERATOR", ""),
                "__EVENTVALIDATION": vs.get("__EVENTVALIDATION", ""),
                "ctl00$MainContent$ddl_dis": district_id,
                "ctl00$MainContent$ddl_sro": "",
                "ctl00$MainContent$dd_regyear": "",
                "propAddress": "",
                "__ASYNCPOST": "true",
            }
            
            try:
                r = s.post(self.base_url, data=payload, timeout=60)
                ajax_result = self.parse_ajax_response(r.text)
                for key in ["__VIEWSTATE", "__EVENTVALIDATION", "__VIEWSTATEGENERATOR"]:
                    if key in ajax_result:
                        vs[key] = ajax_result[key]
            except Exception as e:
                yield {"status": "error", "message": f"District selection failed: {str(e)}"}
                return

            time.sleep(2)

            # 3. Select SRO (AJAX postback)
            yield {"status": "info", "message": f"Selecting SRO {sro_id}..."}
            
            payload.update({
                "ctl00$ScriptManager1": "ctl00$MainContent$UpdatePanel1|ctl00$MainContent$ddl_sro",
                "__EVENTTARGET": "ctl00$MainContent$ddl_sro",
                "__VIEWSTATE": vs.get("__VIEWSTATE", ""),
                "__EVENTVALIDATION": vs.get("__EVENTVALIDATION", ""),
                "ctl00$MainContent$ddl_dis": district_id,
                "ctl00$MainContent$ddl_sro": sro_id,
            })

            try:
                r = s.post(self.base_url, data=payload, timeout=60)
                ajax_result = self.parse_ajax_response(r.text)
                for key in ["__VIEWSTATE", "__EVENTVALIDATION", "__VIEWSTATEGENERATOR"]:
                    if key in ajax_result:
                        vs[key] = ajax_result[key]
            except Exception as e:
                yield {"status": "error", "message": f"SRO selection failed: {str(e)}"}
                return

            time.sleep(2)

            # 4. Select Year (AJAX postback)
            yield {"status": "info", "message": f"Selecting Year {year}..."}
            
            payload.update({
                "ctl00$ScriptManager1": "ctl00$MainContent$UpdatePanel1|ctl00$MainContent$dd_regyear",
                "__EVENTTARGET": "ctl00$MainContent$dd_regyear",
                "__VIEWSTATE": vs.get("__VIEWSTATE", ""),
                "__EVENTVALIDATION": vs.get("__EVENTVALIDATION", ""),
                "ctl00$MainContent$dd_regyear": year,
            })
            
            try:
                r = s.post(self.base_url, data=payload, timeout=60)
                ajax_result = self.parse_ajax_response(r.text)
                for key in ["__VIEWSTATE", "__EVENTVALIDATION", "__VIEWSTATEGENERATOR"]:
                    if key in ajax_result:
                        vs[key] = ajax_result[key]
            except Exception as e:
                yield {"status": "error", "message": f"Year selection failed: {str(e)}"}
                return

            time.sleep(2)

            # 5. Search - FULL PAGE POST (not AJAX!)
            yield {"status": "info", "message": f"Searching for '{name_pattern}'..."}
            
            # Remove AJAX headers for full page post
            s.headers.pop("X-Requested-With", None)
            s.headers.pop("X-MicrosoftAjax", None)
            s.headers["Content-Type"] = "application/x-www-form-urlencoded"
            
            search_payload = {
                "__EVENTTARGET": "",
                "__EVENTARGUMENT": "",
                "__LASTFOCUS": "",
                "__VIEWSTATE": vs.get("__VIEWSTATE", ""),
                "__VIEWSTATEGENERATOR": vs.get("__VIEWSTATEGENERATOR", ""),
                "__EVENTVALIDATION": vs.get("__EVENTVALIDATION", ""),
                "ctl00$MainContent$ddl_dis": district_id,
                "ctl00$MainContent$ddl_sro": sro_id,
                "ctl00$MainContent$dd_regyear": year,
                "propAddress": name_pattern,
                "ctl00$MainContent$btn_prcd": "Search",
            }
            
            try:
                r = s.post(self.base_url, data=search_payload, timeout=60)
                soup = BeautifulSoup(r.content, "html.parser")
                vs = self.get_hidden_fields(soup)
            except Exception as e:
                yield {"status": "error", "message": f"Search failed: {str(e)}"}
                return

            # 6. Pagination Loop
            page_num = 1
            while True:
                # Parse current page
                page_results = self.parse_table(soup)
                count = len(page_results)
                results.extend(page_results)
                
                yield {
                    "status": "data", 
                    "year": year, 
                    "page": page_num, 
                    "count": count, 
                    "data": page_results
                }

                # Check for Next Page
                time.sleep(2)
                
                next_page_arg = self.check_pagination(soup, page_num)
                
                if next_page_arg:
                    yield {"status": "info", "message": f"Navigating to page {page_num + 1}..."}
                    
                    # Full page POST for pagination
                    pagination_payload = {
                        "__EVENTTARGET": "ctl00$MainContent$GridView2",
                        "__EVENTARGUMENT": next_page_arg,
                        "__LASTFOCUS": "",
                        "__VIEWSTATE": vs.get("__VIEWSTATE", ""),
                        "__VIEWSTATEGENERATOR": vs.get("__VIEWSTATEGENERATOR", ""),
                        "__EVENTVALIDATION": vs.get("__EVENTVALIDATION", ""),
                        "ctl00$MainContent$ddl_dis": district_id,
                        "ctl00$MainContent$ddl_sro": sro_id,
                        "ctl00$MainContent$dd_regyear": year,
                        "propAddress": name_pattern,
                    }

                    try:
                        r = s.post(self.base_url, data=pagination_payload, timeout=60)
                        soup = BeautifulSoup(r.content, "html.parser")
                        vs = self.get_hidden_fields(soup)
                        page_num += 1
                    except Exception as e:
                        yield {"status": "error", "message": f"Pagination failed: {str(e)}"}
                        break
                else:
                    break

        yield {"status": "done", "year": year, "total": len(results)}


# Simple test
if __name__ == "__main__":
    scraper = PropertyScraperCore()
    all_data = []
    
    for update in scraper.scrape_year("12", "03", "2019", "A"):
        if update["status"] == "info":
            print(f"[INFO] {update['message']}")
        elif update["status"] == "error":
            print(f"[ERROR] {update['message']}")
        elif update["status"] == "data":
            print(f"[DATA] Year {update['year']}, Page {update['page']}: {update['count']} records")
            all_data.extend(update["data"])
        elif update["status"] == "done":
            print(f"[DONE] Year {update['year']}: Total {update['total']} records")
    
    print(f"\nTotal records collected: {len(all_data)}")
    if all_data:
        print(f"Sample: {all_data[0]}")
