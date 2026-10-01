"""
Library Client for Shanghai Library

本文件是项目的核心业务逻辑层，封装了与上海图书馆VuFind系统的所有交互：
- 图书搜索功能
- 图书详情获取
- 馆藏信息查询
- 封面图片获取

该模块作为API层（api.py）和网络层（client.py）之间的桥梁。
"""
import json
import urllib.parse
from typing import Dict, List, Optional
from .client import HTTPClient
from .parser import LibraryParser
from .models import Book, Availability, SearchResult


class LibraryClient:
    """
    上海图书馆VuFind系统客户端
    
    主要功能:
        - 构建搜索URL
        - 执行图书搜索
        - 获取图书详情
        - 查询馆藏信息
        - 获取封面图片
    
    使用示例:
        client = LibraryClient()
        result = client.search('Python编程')
        if result.success:
            for book in result.books:
                print(book.title)
    
    重要说明:
        - 每次请求创建新实例，避免Cookie污染
        - 所有异常都会被捕获并返回失败结果
    """
    
    BASE_URL = 'https://vufind.library.sh.cn'
    
    SEARCH_TYPE_MAP = {
        'all': 'AllFields',
        'title': 'Title',
        'author': 'Author',
        'publisher': 'Publisher',
        'subject': 'Subject',
        'callnumber': 'CallNumber'
    }
    
    def __init__(self, timeout: int = 15, max_retries: int = 3):
        """
        初始化图书馆客户端
        
        参数:
            timeout: HTTP请求超时时间（秒）
            max_retries: 最大重试次数
        """
        self.http_client = HTTPClient(timeout=timeout, max_retries=max_retries)
        self.parser = LibraryParser()
    
    def build_search_url(self, keyword: str, search_type: str = 'all', page: int = 1, 
                         filters: Optional[Dict] = None) -> str:
        """
        构建搜索URL
        
        参数:
            keyword: 搜索关键词
            search_type: 搜索类型（all、title、author等）
            page: 页码
            filters: 过滤条件字典
        
        返回值:
            完整的搜索URL字符串
        """
        vufind_type = self.SEARCH_TYPE_MAP.get(search_type.lower(), 'AllFields')
        params = [
            ('lookfor', keyword),
            ('type', vufind_type),
            ('page', page)
        ]
        
        if filters:
            if filters.get('publishDate'):
                params.append(('filter[]', f'publishDate:"{filters["publishDate"]}"'))
            if filters.get('language'):
                params.append(('filter[]', f'language:"{filters["language"]}"'))
            if filters.get('format'):
                params.append(('filter[]', f'format:"{filters["format"]}"'))
            if filters.get('callnumber_first'):
                params.append(('filter[]', f'callnumber-first:"{filters["callnumber_first"]}"'))
            if filters.get('callnumber_lcc'):
                params.append(('filter[]', f'callnumber-lcc:"{filters["callnumber_lcc"]}"'))
            if filters.get('loanType'):
                params.append(('filter[]', f'loan_type:"{filters["loanType"]}"'))
            if filters.get('library_name'):
                params.append(('filter[]', f'library_name:"{filters["library_name"]}"'))
        
        query_string = urllib.parse.urlencode(params, safe='[]')
        return f"{self.BASE_URL}/Search/Results?{query_string}"
    
    def search(self, keyword: str, search_type: str = 'all', page: int = 1, limit: int = 20,
               filters: Optional[Dict] = None) -> SearchResult:
        """
        搜索图书
        
        参数:
            keyword: 搜索关键词
            search_type: 搜索类型
            page: 页码
            limit: 返回结果数量限制
            filters: 过滤条件
        
        返回值:
            SearchResult对象，包含搜索结果和状态信息
        """
        try:
            url = self.build_search_url(keyword, search_type, page, filters)
            html = self.http_client.get(url)
            parsed = self.parser.parse_search_results(html)
            
            books = []
            for book_data in parsed['books'][:limit]:
                book = Book(
                    record_id=book_data.get('record_id', ''),
                    title=book_data.get('title', ''),
                    author=book_data.get('author', ''),
                    publisher=book_data.get('publisher', ''),
                    publish_year=book_data.get('publish_year', ''),
                    call_number=book_data.get('call_number', ''),
                    cover_url=book_data.get('cover_url', ''),
                    availability_summary=book_data.get('availability_summary', '')
                )
                books.append(book)
            
            return SearchResult(
                success=True,
                query={'keyword': keyword, 'search_type': search_type},
                statistics={
                    'total_results': parsed.get('total_results', len(books)),
                    'returned_results': len(books),
                    'page': page,
                    'total_pages': parsed.get('total_pages', 1),
                    'has_next': parsed.get('has_next', False)
                },
                books=books
            )
        except Exception as e:
            return SearchResult(
                success=False,
                query={'keyword': keyword, 'search_type': search_type},
                statistics={},
                books=[],
                error=str(e)
            )
    
    def get_book_detail(self, record_id: str) -> Optional[Book]:
        """
        根据record_id获取图书详情
        
        参数:
            record_id: 图书的唯一标识符
        
        返回值:
            Book对象，包含完整图书信息；失败时返回None
        """
        try:
            url = f"{self.BASE_URL}/Record/{record_id}"
            html = self.http_client.get(url)
            parsed = self.parser.parse_book_detail(html)
            
            cover_url = parsed.get('cover_url', '')
            if not cover_url:
                cover_url = f"/Cover/Show?instanceId={record_id}"
            
            return Book(
                record_id=record_id,
                title=parsed.get('title', ''),
                author=parsed.get('author', ''),
                publisher=parsed.get('publisher', ''),
                publish_year=parsed.get('publish_year', ''),
                call_number=parsed.get('call_number', ''),
                cover_url=cover_url,
                isbn=parsed.get('isbn', ''),
                summary=parsed.get('summary') or parsed.get('notes', '')
            )
        except Exception:
            return None
    
    def get_holdings(self, record_id: str) -> List[Availability]:
        """
        获取图书的馆藏信息
        
        参数:
            record_id: 图书的唯一标识符
        
        返回值:
            Availability对象列表，包含所有分馆的馆藏信息
        """
        try:
            url = f"{self.BASE_URL}/Record/{record_id}/AjaxTab"
            html = self.http_client.get(url, params={'tab': 'holdings'})
            parsed = self.parser.parse_holdings(html)
            
            holdings = []
            for holding in parsed:
                availability = Availability(
                    library=holding.get('library', ''),
                    location=holding.get('location', ''),
                    call_number=holding.get('call_number', ''),
                    status=holding.get('status', ''),
                    record_id=record_id,
                    item_id=holding.get('item_id', '')
                )
                holdings.append(availability)

            return holdings
        except Exception:
            return []

    def get_return_date(self, item_id: str) -> str:
        """
        查询单册藏品的预计归还时间

        参数:
            item_id: 单册（物理副本）级ID，来自馆藏页 item-return-date 锚点的
                data-itemid 属性，仅"已借出"状态的馆藏才有

        返回值:
            预计归还日期字符串（YYYY-MM-DD）；失败或暂无数据时返回空串
        """
        try:
            url = f"{self.BASE_URL}/AJAX/JSON"
            html = self.http_client.get(url, params={
                'method': 'itemReturnDate',
                'itemId': item_id
            })
            payload = json.loads(html)
            return str(payload.get('data', '') or '')
        except Exception:
            return ''
    
    def get_full_holdings(self, record_id: str) -> Dict:
        """
        获取完整的馆藏信息（包含统计数据）
        
        参数:
            record_id: 图书的唯一标识符
        
        返回值:
            字典，包含:
                - success: 是否成功
                - record_id: 图书ID
                - holdings: 馆藏列表
                - available_count: 可借数量
                - total_count: 总馆藏数量
        """
        holdings = self.get_holdings(record_id)
        available_count = sum(1 for h in holdings if h.is_available())
        
        return {
            'success': True,
            'record_id': record_id,
            'holdings': [h.to_dict() for h in holdings],
            'available_count': available_count,
            'total_count': len(holdings)
        }
    
    def get_cover_url(self, record_id: str) -> str:
        """
        获取封面图片URL
        
        参数:
            record_id: 图书的唯一标识符
        
        返回值:
            封面图片的完整URL
        """
        return f"{self.BASE_URL}/Cover/Show?instanceId={record_id}"
    
    def proxy_cover(self, record_id: str) -> bytes:
        """
        代理获取封面图片（解决跨域问题）
        
        参数:
            record_id: 图书的唯一标识符
        
        返回值:
            图片的原始字节数据；失败时返回空字节
        """
        try:
            url = self.get_cover_url(record_id)
            return self.http_client.get_bytes(url)
        except Exception:
            return b''
