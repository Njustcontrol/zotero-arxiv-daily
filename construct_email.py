from paper import ArxivPaper
import math
from tqdm import tqdm
from email.header import Header
from email.mime.text import MIMEText
from email.utils import parseaddr, formataddr
import smtplib
import datetime
from loguru import logger

framework = """
<!DOCTYPE HTML>
<html>
<head>
  <style>
    .star-wrapper {
      font-size: 1.3em; /* 调整星星大小 */
      line-height: 1; /* 确保垂直对齐 */
      display: inline-flex;
      align-items: center; /* 保持对齐 */
    }
    .half-star {
      display: inline-block;
      width: 0.5em; /* 半颗星的宽度 */
      overflow: hidden;
      white-space: nowrap;
      vertical-align: middle;
    }
    .full-star {
      vertical-align: middle;
    }
  </style>
</head>
<body>

<div>
    __CONTENT__
</div>

<br><br>
<div>
To unsubscribe, remove your email in your Github Action setting.
</div>

</body>
</html>
"""

def get_empty_html():
  block_template = """
  <table border="0" cellpadding="0" cellspacing="0" width="100%" style="font-family: Arial, sans-serif; border: 1px solid #ddd; border-radius: 8px; padding: 16px; background-color: #f9f9f9;">
  <tr>
    <td style="font-size: 20px; font-weight: bold; color: #333;">
        No Papers Today. Take a Rest!
    </td>
  </tr>
  </table>
  """
  return block_template

def get_block_html(title:str, authors:str, rate:str,arxiv_id:str, abstract:str, pdf_url:str, code_url:str=None, affiliations:str=None):
    code = f'<a href="{code_url}" style="display: inline-block; text-decoration: none; font-size: 14px; font-weight: bold; color: #fff; background-color: #5bc0de; padding: 8px 16px; border-radius: 4px; margin-left: 8px;">Code</a>' if code_url else ''
    block_template = """
    <table border="0" cellpadding="0" cellspacing="0" width="100%" style="font-family: Arial, sans-serif; border: 1px solid #ddd; border-radius: 8px; padding: 16px; background-color: #f9f9f9;">
    <tr>
        <td style="font-size: 20px; font-weight: bold; color: #333;">
            {title}
        </td>
    </tr>
    <tr>
        <td style="font-size: 14px; color: #666; padding: 8px 0;">
            {authors}
            <br>
            <i>{affiliations}</i>
        </td>
    </tr>
    <tr>
        <td style="font-size: 14px; color: #333; padding: 8px 0;">
            <strong>Relevance:</strong> {rate}
        </td>
    </tr>
    <tr>
        <td style="font-size: 14px; color: #333; padding: 8px 0;">
            <strong>arXiv ID:</strong> {arxiv_id}
        </td>
    </tr>
    <tr>
        <td style="font-size: 14px; color: #333; padding: 8px 0;">
            <strong>TLDR:</strong> {abstract}
        </td>
    </tr>

    <tr>
        <td style="padding: 8px 0;">
            <a href="{pdf_url}" style="display: inline-block; text-decoration: none; font-size: 14px; font-weight: bold; color: #fff; background-color: #d9534f; padding: 8px 16px; border-radius: 4px;">PDF</a>
            {code}
        </td>
    </tr>
</table>
"""
    return block_template.format(title=title, authors=authors,rate=rate,arxiv_id=arxiv_id, abstract=abstract, pdf_url=pdf_url, code=code, affiliations=affiliations)

def get_stars(score:float):
    full_star = '<span class="full-star">⭐</span>'
    half_star = '<span class="half-star">⭐</span>'
    low = 6
    high = 8
    if score <= low:
        return ''
    elif score >= high:
        return full_star * 5
    else:
        interval = (high-low) / 10
        star_num = math.ceil((score-low) / interval)
        full_star_num = int(star_num/2)
        half_star_num = star_num - full_star_num * 2
        return '<div class="star-wrapper">'+full_star * full_star_num + half_star * half_star_num + '</div>'


# --- 用下面的代码替换掉你现有的整个 render_email 函数 ---
def render_email(papers: list[ArxivPaper]):
    parts = []
    if len(papers) == 0:
        return framework.replace('__CONTENT__', get_empty_html())

    print("开始渲染邮件内容，将逐一处理每篇论文...")
    for p in tqdm(papers, desc='Rendering Email'):
        try:
            # 将对单篇论文的所有处理逻辑，全部放入 try 块中
            # 这样，无论哪一步出错，都能被捕获

            rate = get_stars(p.score)
            
            authors = [a.name for a in p.authors[:5]]
            authors = ', '.join(authors)
            if len(p.authors) > 5:
                authors += ', ...'
            
            # 这一行就是最开始出错的地方，现在它被 try...except 保护起来了
            if p.affiliations is not None:
                affiliations = p.affiliations[:5]
                affiliations = ', '.join(affiliations)
                if len(p.affiliations) > 5:
                    affiliations += ', ...'
            else:
                affiliations = 'Unknown Affiliation'
            
            # 将成功处理的论文信息添加到 parts 列表中
            parts.append(get_block_html(p.title, authors, rate, p.arxiv_id, p.tldr, p.pdf_url, p.code_url, affiliations))

        except Exception as e:
            # 使用一个更通用的 Exception 来捕获所有可能的错误，而不仅仅是 AttributeError
            # 这样代码更健壮
            
            # 尝试获取论文ID用于打印日志，如果连ID都获取不到，就给一个默认提示
            try:
                paper_id = p.arxiv_id
            except AttributeError:
                paper_id = "未知ID的论文"
                
            print(f"\n[警告] 跳过论文 {paper_id}，因为它在处理过程中导致了一个错误: {e}\n")
            continue  # 跳过这篇有问题的论文，继续处理下一篇

    if not parts:
        print("所有论文在处理时都出错或被跳过，生成一封空邮件。")
        return framework.replace('__CONTENT__', get_empty_html())

    content = '<br>' + '</br><br>'.join(parts) + '</br>'
    return framework.replace('__CONTENT__', content)

# --- 替换结束 ---

def send_email(sender:str, receiver:str, password:str,smtp_server:str,smtp_port:int, html:str,):
    def _format_addr(s):
        name, addr = parseaddr(s)
        return formataddr((Header(name, 'utf-8').encode(), addr))

    msg = MIMEText(html, 'html', 'utf-8')
    msg['From'] = _format_addr('Github Action <%s>' % sender)
    msg['To'] = _format_addr('You <%s>' % receiver)
    today = datetime.datetime.now().strftime('%Y/%m/%d')
    msg['Subject'] = Header(f'Daily arXiv {today}', 'utf-8').encode()

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
    except Exception as e:
        logger.warning(f"Failed to use TLS. {e}")
        logger.warning(f"Try to use SSL.")
        server = smtplib.SMTP_SSL(smtp_server, smtp_port)

    server.login(sender, password)
    server.sendmail(sender, [receiver], msg.as_string())
    server.quit()
