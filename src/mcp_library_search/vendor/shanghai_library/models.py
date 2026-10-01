"""
Data models for Shanghai Library Book Search System

本文件定义了项目中使用的所有数据模型，包括：
- Book: 图书信息模型
- Availability: 馆藏信息模型
- SearchResult: 搜索结果模型

这些模型用于在不同模块之间传递数据，确保数据结构的一致性。
"""
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional


@dataclass
class Book:
    """
    图书数据模型
    
    存储一本图书的完整信息，包括基本信息和馆藏状态
    
    字段说明:
        record_id: 图书的唯一标识符，用于在图书馆系统中定位图书
        title: 图书标题
        author: 作者信息
        publisher: 出版社信息
        publish_year: 出版年份
        call_number: 索书号
        cover_url: 封面图片URL
        availability_summary: 可用性摘要信息
        isbn: ISBN编号
        summary: 图书内容摘要
        availability: 馆藏信息列表
    """
    record_id: str
    title: str
    author: str = ""
    publisher: str = ""
    publish_year: str = ""
    call_number: str = ""
    cover_url: str = ""
    availability_summary: str = ""
    isbn: str = ""
    summary: str = ""
    availability: Optional[List['Availability']] = None
    
    def to_dict(self) -> Dict:
        """
        将Book对象转换为字典格式
        
        返回值:
            包含图书所有信息的字典，适合序列化为JSON
        """
        result = asdict(self)
        if self.availability:
            result['availability'] = [a.to_dict() for a in self.availability]
        return result


@dataclass
class Availability:
    """
    馆藏可用性数据模型
    
    存储一本图书在某个图书馆的具体馆藏信息和借阅状态
    
    字段说明:
        library: 图书馆名称
        location: 馆藏位置（如书架号）
        call_number: 索书号
        status: 借阅状态（如"可借"、"已借出"）
        record_id: 所属图书的record_id
        item_id: 单册（物理副本）级ID，已借出的馆藏用于查询预计归还时间
        due_date: 预计归还时间（YYYY-MM-DD），需另行调用 itemReturnDate 接口获取
    """
    library: str = ""
    location: str = ""
    call_number: str = ""
    status: str = ""
    record_id: str = ""
    item_id: str = ""
    due_date: str = ""
    
    def is_available(self) -> bool:
        """
        判断图书是否可借阅
        
        通过检查status字段中的关键词来判断是否可借
        
        返回值:
            True表示可借，False表示不可借
        """
        available_keywords = ["可借", "已归还", "在馆", "Available"]
        unavailable_keywords = ["已借出", "外借", "丢失", "Loaned out", "Lost"]
        
        status_lower = self.status.lower()
        if any(keyword.lower() in status_lower for keyword in unavailable_keywords):
            return False
        return any(keyword.lower() in status_lower for keyword in available_keywords)
    
    def to_dict(self) -> Dict:
        """
        将Availability对象转换为字典格式
        
        返回值:
            包含馆藏所有信息的字典
        """
        return asdict(self)


@dataclass
class SearchResult:
    """
    搜索结果数据模型
    
    封装一次搜索操作的完整结果，包括状态信息、统计数据和图书列表
    
    字段说明:
        success: 搜索是否成功
        query: 搜索查询条件
        statistics: 搜索统计信息（总数、页数等）
        books: 搜索到的图书列表
        error: 错误信息（如搜索失败）
    """
    success: bool
    query: Dict
    statistics: Dict
    books: Optional[List[Book]] = None
    error: str = ""
    
    def to_dict(self) -> Dict:
        """
        将SearchResult对象转换为字典格式
        
        返回值:
            包含搜索结果所有信息的字典，适合序列化为JSON
        """
        result = {
            "success": self.success,
            "query": self.query,
            "statistics": self.statistics,
            "error": self.error
        }
        if self.books:
            result["books"] = [book.to_dict() for book in self.books]
        else:
            result["books"] = []
        return result
