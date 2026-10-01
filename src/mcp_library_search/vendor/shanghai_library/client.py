"""
HTTP Client with retry mechanism and cookie management

本文件实现了一个增强的HTTP客户端，提供以下功能：
- 自动重试机制，处理网络不稳定情况
- Cookie管理，保持会话状态
- 压缩响应自动解压（gzip、br、deflate）
- 模拟浏览器User-Agent，避免被识别为爬虫

该模块是项目的基础网络层，被library_client模块调用。
"""
import urllib.request
import urllib.parse
import urllib.error
import time
from typing import Dict, Optional


class HTTPClient:
    """
    带重试机制和Cookie管理的HTTP客户端
    
    主要功能:
        - 发送HTTP GET请求
        - 自动处理网络错误并重试
        - 管理会话Cookie
        - 自动解压压缩响应
        - 支持返回文本或原始字节
    
    使用示例:
        client = HTTPClient(timeout=10, max_retries=3)
        html = client.get('https://example.com')
        image_data = client.get_bytes('https://example.com/image.jpg')
    """
    
    DEFAULT_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0'
    }
    
    def __init__(self, timeout: int = 15, max_retries: int = 3, retry_delay: float = 1.0):
        """
        初始化HTTP客户端
        
        参数:
            timeout: 请求超时时间（秒）
            max_retries: 最大重试次数
            retry_delay: 重试之间的延迟（秒）
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.cookies: Dict[str, str] = {}
    
    def get(self, url: str, params: Optional[Dict] = None, headers: Optional[Dict] = None) -> str:
        """
        发送GET请求，返回文本内容
        
        参数:
            url: 请求URL
            params: URL查询参数字典
            headers: 额外的HTTP头
        
        返回值:
            响应文本（UTF-8解码）
        
        异常:
            当所有重试都失败时抛出最后一个异常
        """
        if params:
            query_string = urllib.parse.urlencode(params)
            url = f"{url}?{query_string}" if '?' not in url else f"{url}&{query_string}"
        
        request_headers = {**self.DEFAULT_HEADERS}
        if headers:
            request_headers.update(headers)
        if self.cookies:
            cookie_string = '; '.join(f'{k}={v}' for k, v in self.cookies.items())
            request_headers['Cookie'] = cookie_string
        
        last_error = None
        for attempt in range(self.max_retries):
            try:
                request = urllib.request.Request(url, headers=request_headers)
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    self._extract_cookies(response)
                    content = response.read()
                    encoding = response.headers.get('Content-Encoding', '')
                    if encoding == 'gzip':
                        import gzip
                        content = gzip.decompress(content)
                    elif encoding == 'br':
                        import brotli
                        content = brotli.decompress(content)
                    elif encoding == 'deflate':
                        import zlib
                        content = zlib.decompress(content)
                    return content.decode('utf-8')
            except urllib.error.URLError as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
        
        raise last_error
    
    def get_bytes(self, url: str, params: Optional[Dict] = None, headers: Optional[Dict] = None) -> bytes:
        """
        发送GET请求，返回原始字节（用于图片等二进制数据）
        
        参数:
            url: 请求URL
            params: URL查询参数字典
            headers: 额外的HTTP头
        
        返回值:
            响应的原始字节数据
        
        异常:
            当所有重试都失败时抛出最后一个异常
        """
        if params:
            query_string = urllib.parse.urlencode(params)
            url = f"{url}?{query_string}" if '?' not in url else f"{url}&{query_string}"
        
        request_headers = {**self.DEFAULT_HEADERS}
        if headers:
            request_headers.update(headers)
        if self.cookies:
            cookie_string = '; '.join(f'{k}={v}' for k, v in self.cookies.items())
            request_headers['Cookie'] = cookie_string
        
        last_error = None
        for attempt in range(self.max_retries):
            try:
                request = urllib.request.Request(url, headers=request_headers)
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    self._extract_cookies(response)
                    content = response.read()
                    encoding = response.headers.get('Content-Encoding', '')
                    if encoding == 'gzip':
                        import gzip
                        content = gzip.decompress(content)
                    elif encoding == 'br':
                        import brotli
                        content = brotli.decompress(content)
                    elif encoding == 'deflate':
                        import zlib
                        content = zlib.decompress(content)
                    return content
            except urllib.error.URLError as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
        
        raise last_error
    
    def _extract_cookies(self, response) -> None:
        """
        从响应头中提取并保存Cookie
        
        参数:
            response: urllib的响应对象
        """
        if 'Set-Cookie' in response.headers:
            cookie_header = response.headers['Set-Cookie']
            for cookie in cookie_header.split(','):
                if '=' in cookie:
                    name_value = cookie.split(';')[0].strip()
                    if '=' in name_value:
                        name, value = name_value.split('=', 1)
                        self.cookies[name.strip()] = value.strip()
