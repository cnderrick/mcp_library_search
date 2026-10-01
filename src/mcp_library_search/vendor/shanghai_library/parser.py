"""
上海图书馆网站HTML解析器

这个模块负责解析从上海图书馆网站获取的HTML页面，提取图书信息、搜索结果和馆藏数据。

主要类:
- LibraryParser: 提供统一的解析接口
- SearchResultsParser: 解析搜索结果页面
- BookDetailParser: 解析图书详情页面
- HoldingsParser: 解析馆藏信息页面

作者: 上海图书馆搜索系统团队
日期: 2026-04-18
"""
from html.parser import HTMLParser
from typing import List, Dict, Optional
import re


class LibraryParser:
    """
    上海图书馆HTML页面解析器
    
    提供统一的解析接口，封装了三个专业解析器的功能。
    
    主要方法:
    - parse_search_results: 解析搜索结果页面
    - parse_book_detail: 解析图书详情页面
    - parse_holdings: 解析馆藏信息页面
    """
    
    def __init__(self):
        pass
    
    def parse_search_results(self, html: str) -> Dict:
        """
        解析搜索结果页面
        
        参数:
            html (str): 搜索结果页面的HTML内容
            
        返回:
            Dict: 包含以下键的字典
                - books: 图书列表
                - total_results: 总结果数
                - total_pages: 总页数
                - current_page: 当前页码
        """
        parser = SearchResultsParser()
        parser.feed(html)
        return {
            'books': parser.books,
            'total_results': parser.total_results,
            'total_pages': parser.total_pages,
            'current_page': parser.current_page,
            'has_next': parser.has_next
        }
    
    def parse_book_detail(self, html: str) -> Dict:
        """
        解析图书详情页面
        
        参数:
            html (str): 图书详情页面的HTML内容
            
        返回:
            Dict: 包含图书详细信息的字典
                - record_id: 图书ID
                - title: 书名
                - author: 作者
                - publisher: 出版社
                - publish_year: 出版年
                - call_number: 索书号
                - cover_url: 封面图片URL
                - isbn: ISBN号
                - summary: 内容简介
        """
        parser = BookDetailParser()
        parser.feed(html)
        return parser.book_info
    
    def parse_holdings(self, html: str) -> List[Dict]:
        """
        解析馆藏信息页面
        
        参数:
            html (str): 馆藏信息页面的HTML内容
            
        返回:
            List[Dict]: 馆藏信息列表，每个字典包含
                - library: 图书馆名称
                - location: 馆藏地点
                - call_number: 索书号
                - status: 借阅状态
        """
        parser = HoldingsParser()
        parser.feed(html)
        return parser.holdings


class SearchResultsParser(HTMLParser):
    """
    搜索结果页面解析器 - 针对VuFind结构优化
    
    继承自HTMLParser，使用事件驱动的方式解析搜索结果页面，
    提取图书信息、统计数据和分页信息。
    
    主要属性:
        - books: 解析出的图书列表
        - total_results: 总结果数
        - total_pages: 总页数
        - current_page: 当前页码
    """
    
    def __init__(self):
        super().__init__()
        self.books = []
        self.total_results = 0
        self.total_pages = 1
        self.current_page = 1
        self.current_book = None
        self.in_result = False
        self.in_title = False
        self.in_author = False
        self.in_author_span = False
        self.in_result_body = False
        self.in_pagination = False
        self.in_pagination_link = False
        self.current_text = ""
        self.depth = 0
        self.result_depth = 0
        self.result_body_depth = 0
        self.pending_text = ""
        self.pagination_links = []
        self.in_stats = False
        self.found_total = False
        self.has_next = False
    
    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        class_name = attrs_dict.get('class', '')
        element_id = attrs_dict.get('id', '')
        href = attrs_dict.get('href', '')
        
        if tag == 'div' and ('stats' in class_name.lower() or 'result-top' in class_name.lower() or 'search-stats' in class_name.lower()):
            self.in_stats = True
            self.current_text = ""

        if tag == 'a' and 'page-next' in class_name.split():
            self.has_next = True
        
        if tag == 'div' and 'result' in class_name.split() and element_id.startswith('result'):
            self.in_result = True
            self.result_depth = self.depth
            self.current_book = {
                'record_id': '',
                'title': '',
                'author': '',
                'publisher': '',
                'publish_year': '',
                'call_number': '',
                'cover_url': '',
                'availability_summary': ''
            }
        
        if self.in_result:
            if tag == 'div' and 'result-body' in class_name.split():
                self.in_result_body = True
                self.result_body_depth = self.depth
            
            if tag == 'span' and 'author-data' in class_name.split():
                self.in_author_span = True
            
            if tag == 'a':
                if '/Record/' in href:
                    match = re.search(r'/Record/([^"?/]+)', href)
                    if match:
                        record_id = match.group(1)
                        if not self.current_book['record_id']:
                            self.current_book['record_id'] = record_id
                        if 'title' in class_name.split():
                            self.in_title = True
                            self.current_text = ""
                
                if self.in_author_span and 'type=Author' in href:
                    self.in_author = True
                    self.current_text = ""
            
            if tag == 'img':
                src = attrs_dict.get('src', '')
                if src and 'Cover' in src and not self.current_book['cover_url']:
                    self.current_book['cover_url'] = src
            
            if tag == 'br':
                self.process_pending_text()
        
        if tag == 'ul' and 'pagination' in class_name.split():
            self.in_pagination = True
        
        if self.in_pagination and tag == 'a':
            href = attrs_dict.get('href', '')
            if 'page=' in href:
                self.in_pagination_link = True
                self.current_text = ""
        
        self.depth += 1
    
    def process_pending_text(self):
        if self.pending_text and self.current_book:
            text = self.pending_text.strip()
            if '出版社' in text:
                match = re.search(r'出版社[：:]\s*(.+?)(?:\s*$)', text)
                if match:
                    publisher = match.group(1).strip()
                    if publisher:
                        self.current_book['publisher'] = publisher
            
            if '出版时间' in text:
                match = re.search(r'出版时间[：:]\s*(\d{4})', text)
                if match:
                    self.current_book['publish_year'] = match.group(1)
            
            if '索书号' in text:
                match = re.search(r'索书号[：:]\s*(.+?)(?:\s*$)', text)
                if match:
                    call_number = match.group(1).strip()
                    if call_number:
                        self.current_book['call_number'] = call_number
            
            self.pending_text = ""
    
    def handle_endtag(self, tag):
        self.depth -= 1
        
        if tag == 'div' and self.in_stats:
            self.in_stats = False
            if self.current_text and not self.found_total:
                match = re.search(r'(\d+)\s*条', self.current_text)
                if match:
                    self.total_results = int(match.group(1))
                    self.found_total = True
        
        if self.in_result and self.depth <= self.result_depth:
            self.process_pending_text()
            if self.current_book and self.current_book.get('record_id'):
                self.books.append(self.current_book)
            self.in_result = False
            self.in_result_body = False
            self.in_author_span = False
            self.current_book = None
        
        if tag == 'div' and self.in_result_body and self.depth < self.result_body_depth:
            self.process_pending_text()
            self.in_result_body = False
        
        if tag == 'span' and self.in_author_span:
            self.in_author_span = False
        
        if tag == 'a':
            if self.in_title and self.current_book:
                self.current_book['title'] = self.current_text.strip()
            elif self.in_author and self.current_book:
                self.current_book['author'] = self.current_text.strip()
            elif self.in_pagination_link:
                try:
                    page_num = int(self.current_text.strip())
                    self.pagination_links.append(page_num)
                except ValueError:
                    pass
            self.in_title = False
            self.in_author = False
            self.in_pagination_link = False
        
        if tag == 'ul' and self.in_pagination:
            self.in_pagination = False
            if self.pagination_links:
                self.total_pages = max(self.pagination_links)
    
    def handle_data(self, data):
        data = data.strip()
        if not data:
            return
        
        if self.in_stats:
            if self.current_text:
                self.current_text += " " + data
            else:
                self.current_text = data
        
        if self.in_title or self.in_author or self.in_pagination_link:
            if self.current_text:
                self.current_text += " " + data
            else:
                self.current_text = data
        
        if self.in_result_body and self.current_book:
            if self.pending_text:
                self.pending_text += " " + data
            else:
                self.pending_text = data


class BookDetailParser(HTMLParser):
    """
    图书详情页面解析器 - 提取图书元数据
    
    继承自HTMLParser，解析图书详情页面，提取书名、作者、出版社、
    ISBN、索书号、出版年、封面图片和内容简介等信息。
    
    主要属性:
        - book_info: 解析出的图书信息字典
    """
    
    def __init__(self):
        super().__init__()
        self.book_info = {
            'record_id': '',
            'title': '',
            'author': '',
            'publisher': '',
            'publish_year': '',
            'call_number': '',
            'cover_url': '',
            'isbn': '',
            'summary': ''
        }
        self.current_text = ""
        self.in_title = False
        self.in_author = False
        self.in_publisher = False
        self.in_isbn = False
        self.in_summary = False
        self.in_publish_year = False
        self.current_th = ""
        self.in_td = False
        self.in_th = False
    
    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        class_name = attrs_dict.get('class', '')
        property_name = attrs_dict.get('property', '')
        
        if tag == 'h3' and property_name == 'name':
            self.in_title = True
            self.current_text = ""
        
        if tag == 'span':
            classes = class_name.split()
            if 'author-data' in classes:
                self.in_author = True
                self.current_text = ""
            elif property_name == 'publisher':
                self.in_publisher = True
                self.current_text = ""
        
        if tag == 'a' and self.in_author:
            self.current_text = ""
        
        if tag == 'img':
            src = attrs_dict.get('src', '')
            if src and 'Cover' in src:
                self.book_info['cover_url'] = src
        
        if tag == 'th':
            self.in_th = True
            self.current_text = ""
        
        if tag == 'td':
            self.in_td = True
            self.current_text = ""
        
        if tag == 'div' and 'summary' in class_name.lower():
            self.in_summary = True
            self.current_text = ""
    
    def handle_endtag(self, tag):
        if tag == 'h3' and self.in_title:
            self.book_info['title'] = self.current_text.strip()
            self.in_title = False
            self.current_text = ""
        
        if tag == 'a' and self.in_author:
            self.book_info['author'] = self.current_text.strip()
            self.in_author = False
            self.current_text = ""
        
        if tag == 'span' and self.in_publisher:
            self.book_info['publisher'] = self.current_text.strip()
            self.in_publisher = False
            self.current_text = ""
        
        if tag == 'th' and self.in_th:
            self.current_th = self.current_text.strip()
            self.in_th = False
            self.current_text = ""
        
        if tag == 'td' and self.in_td:
            text = self.current_text.strip()
            th_lower = self.current_th.lower()
            
            if 'isbn' in th_lower:
                isbn_match = re.search(r'[\d\-]+', text)
                if isbn_match:
                    self.book_info['isbn'] = isbn_match.group()
            elif '出版' in self.current_th and ('日期' in self.current_th or '时间' in self.current_th or '年' in self.current_th):
                year_match = re.search(r'(\d{4})', text)
                if year_match:
                    self.book_info['publish_year'] = year_match.group(1)
            elif '索书号' in self.current_th:
                self.book_info['call_number'] = text
            elif '附注' in self.current_th:
                # 站点没有独立简介区块，内容简介常以"附注"字段（MARC 500）形式给出
                if self.book_info.get('notes'):
                    self.book_info['notes'] += f"\n{text}"
                else:
                    self.book_info['notes'] = text
            
            self.in_td = False
            self.current_text = ""
        
        if tag == 'div' and self.in_summary:
            self.book_info['summary'] = self.current_text.strip()
            self.in_summary = False
            self.current_text = ""
    
    def handle_data(self, data):
        data = data.strip()
        if not data:
            return
        
        if self.in_title or self.in_author or self.in_publisher or self.in_th or self.in_td or self.in_summary:
            if self.current_text:
                self.current_text += " " + data
            else:
                self.current_text = data


class HoldingsParser(HTMLParser):
    """
    馆藏信息解析器 - 从AjaxTab端点解析馆藏数据
    
    继承自HTMLParser，解析馆藏信息页面，提取各图书馆的馆藏地点、
    索书号和借阅状态等信息。
    
    主要属性:
        - holdings: 解析出的馆藏信息列表
        - current_library: 当前解析的图书馆名称
    """
    
    def __init__(self):
        super().__init__()
        self.holdings = []
        self.current_holding = None
        self.current_library = ""
        self.current_location = ""
        self.current_text = ""
        self.in_call_number = False
        self.in_barcode = False
        self.in_status = False
        self.in_library = False
        self.in_location = False
        self.in_h3 = False
        self.pending_library = ""
        self.pending_location = ""
        self.found_library = False
        self.found_location = False
    
    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        class_name = attrs_dict.get('class', '')
        
        if tag == 'h3':
            self.in_h3 = True
            self.current_text = ""
            self.found_library = False
            self.found_location = False
        
        if tag == 'span':
            classes = class_name.split()
            if 'callnumber' in classes:
                self.in_call_number = True
                self.current_text = ""
            elif 'barcode' in classes:
                self.in_barcode = True
                self.current_text = ""
            elif 'availability' in classes:
                self.in_status = True
                self.current_text = ""
        
        if tag == 'tr':
            self.current_holding = {
                'library': self.current_library,
                'location': self.current_location,
                'call_number': '',
                'status': '',
                'record_id': '',
                'item_id': '',
                'due_date': ''
            }

        if tag == 'a' and 'item-return-date' in class_name.split():
            # "预计归还时间"日历图标：data-itemid 是单册（物理副本）级 ID，
            # 归还日期需另行调用 itemReturnDate 接口获取
            if self.current_holding is not None:
                self.current_holding['item_id'] = attrs_dict.get('data-itemid', '')
    
    def handle_endtag(self, tag):
        if tag == 'h3' and self.in_h3:
            text = self.current_text.strip()
            if '所属馆' in text:
                self.current_library = text.replace('所属馆:', '').replace('所属馆：', '').strip()
            elif text:
                self.current_library = text
            self.in_h3 = False
            self.current_text = ""
        
        if tag == 'span':
            if self.in_call_number and self.current_holding:
                self.current_holding['call_number'] = self.current_text.strip()
                self.in_call_number = False
            elif self.in_barcode and self.current_holding:
                self.current_holding['location'] = self.current_text.strip()
                self.in_barcode = False
            elif self.in_status and self.current_holding:
                self.current_holding['status'] = self.current_text.strip()
                self.in_status = False
            self.current_text = ""
        
        if tag == 'tr' and self.current_holding:
            if self.current_holding.get('call_number') or self.current_holding.get('status'):
                self.holdings.append(self.current_holding)
            self.current_holding = None
    
    def handle_data(self, data):
        data = data.strip()
        if not data:
            return
        
        if self.in_h3 or self.in_call_number or self.in_barcode or self.in_status:
            if self.current_text:
                self.current_text += " " + data
            else:
                self.current_text = data
        
        if '所属馆' in data:
            match = re.search(r'所属馆[：:]\s*(.+)', data)
            if match:
                self.current_library = match.group(1).strip()
        
        if self.current_holding:
            if '已归还' in data or '可借' in data or '在馆' in data or 'Available' in data:
                status = data
                if 'Available' in data:
                    status = data.replace('Available', '已归还')
                self.current_holding['status'] = status
            elif '已借出' in data or '外借' in data or 'Loaned out' in data:
                status = data
                if 'Loaned out' in data:
                    status = '已借出'
                self.current_holding['status'] = status
            elif '丢失' in data or '馆藏丢失' in data or 'Lost' in data:
                status = data
                if 'Lost' in data:
                    status = '馆藏丢失'
                self.current_holding['status'] = status
