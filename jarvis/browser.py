import asyncio
from playwright.async_api import async_playwright
import re

class BrowserAgent:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None

    async def init(self):
        if not self.browser:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=False)
            self.page = await self.browser.new_page(user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

    async def search(self, query: str):
        await self.init()
        url = f"https://html.duckduckgo.com/html/?q={query}"
        await self.page.goto(url)
        results = await self.page.eval_on_selector_all('.result', '''
            elements => elements.slice(0, 5).map(el => {
                const titleEl = el.querySelector('.result__title');
                const snippetEl = el.querySelector('.result__snippet');
                return {
                    title: titleEl ? titleEl.innerText : '',
                    url: titleEl ? titleEl.querySelector('a').href : '',
                    snippet: snippetEl ? snippetEl.innerText : ''
                };
            })
        ''')
        return results

    async def visit(self, url: str):
        await self.init()
        await self.page.goto(url)
        
        text = await self.page.evaluate('''
            () => {
                const removeSelectors = ['nav', 'footer', 'header', 'aside', 'script', 'style', 'iframe', 'ins', '.ad', '#ad'];
                removeSelectors.forEach(sel => {
                    document.querySelectorAll(sel).forEach(el => el.remove());
                });
                return document.body.innerText;
            }
        ''')
        return {"url": url, "content": text[:5000]}

    async def screenshot(self, url: str, path: str = None):
        await self.init()
        await self.page.goto(url)
        if not path:
            path = "data/screenshot.png"
        await self.page.screenshot(path=path, full_page=True)
        return path

    async def research(self, topic: str):
        results = await self.search(topic)
        summary = {"topic": topic, "sources": []}
        for res in results[:3]:
            try:
                page_data = await self.visit(res['url'])
                summary["sources"].append({
                    "title": res['title'],
                    "url": res['url'],
                    "snippet": res['snippet'],
                    "content": page_data['content'][:1500]
                })
            except:
                pass
        return summary

    async def close(self):
        if self.browser:
            await self.browser.close()
            await self.playwright.stop()
            self.browser = None

_agent = BrowserAgent()

async def search(query): return await _agent.search(query)
async def visit(url): return await _agent.visit(url)
async def screenshot(url, path=None): return await _agent.screenshot(url, path)
async def research(topic): return await _agent.research(topic)
async def close(): return await _agent.close()
