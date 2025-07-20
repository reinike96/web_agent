import html2text
from bs4 import BeautifulSoup

class Perception:
    """
    Processes the HTML of a web page to extract relevant information
    for the LLM, such as interactive elements and simplified content.
    """
    def __init__(self, html_content: str):
        """Initializes with the HTML content of a page."""
        self.soup = BeautifulSoup(html_content, 'html.parser')
        self.html = html_content

    def _get_selector(self, element) -> str:
        """
        Generates a CSS selector for a BeautifulSoup element.
        Prioritizes ID, then other attributes for stability.
        """
        if element.get('id'):
            return f"#{element.get('id')}"
        
        # Fallback to other attributes
        if element.get('name'):
            return f"{element.name}[name='{element.get('name')}']"
        if element.get('class'):
            # Use the first class if multiple exist
            return f".{element.get('class')[0]}"
        
        # Basic tag name as a last resort
        return element.name

    def get_interactive_elements(self) -> list[dict]:
        """
        Finds all interactive elements and returns them with selectors.
        """
        elements = []
        # Links
        for link in self.soup.find_all('a', href=True):
            elements.append({
                'type': 'link',
                'text': link.get_text(strip=True),
                'selector': self._get_selector(link)
            })
        # Buttons
        for button in self.soup.find_all('button'):
            elements.append({
                'type': 'button',
                'text': button.get_text(strip=True),
                'selector': self._get_selector(button)
            })
        # Inputs
        for input_tag in self.soup.find_all('input', {'type': ['text', 'search', 'email', 'password', 'submit']}):
            elements.append({
                'type': 'input',
                'text': input_tag.get('value') or input_tag.get('placeholder', ''),
                'selector': self._get_selector(input_tag)
            })
        return elements

    def get_page_summary(self, character_limit: int = 2000) -> str:
        """
        Generates a summarized, optimized representation of the page for the LLM.
        """
        # 1. Page Title
        title = self.soup.title.string if self.soup.title else "No Title"
        
        # 2. Simplified Text Content
        h = html2text.HTML2Text()
        h.ignore_links = True
        h.ignore_images = True
        page_text = h.handle(self.html)
        truncated_text = (page_text[:400] + '...') if len(page_text) > 400 else page_text

        # 3. Interactive Elements
        interactive_elements = self.get_interactive_elements()
        elements_summary = []
        for elem in interactive_elements:
            elements_summary.append(
                f"- Type: {elem['type']}, Selector: `{elem['selector']}`, Text: '{elem.get('text', '')[:50]}'"
            )

        # 4. Combine into a single string
        summary = (
            f"Page Title: {title}\n\n"
            f"Content Preview:\n---\n{truncated_text}\n---\n\n"
            f"Interactive Elements:\n" +
            "\n".join(elements_summary)
        )

        # Ensure it's within the character limit
        return summary[:character_limit]
if __name__ == '__main__':
    # Example Usage
    sample_html = """
    <html>
    <body>
        <h1>Welcome</h1>
        <p>This is a sample page.</p>
        <a href="/page2">Go to Page 2</a>
        <button id="submit-btn">Submit</button>
        <input type="text" name="username" id="user-input">
    </body>
    </html>
    """
    perception_module = Perception(sample_html)
    
    print("--- Interactive Elements ---")
    interactive_elements = perception_module.get_interactive_elements()
    for element in interactive_elements:
        print(element)

    print("\n--- Simplified HTML (Markdown) ---")
    simplified_html = perception_module.get_simplified_html()
    print(simplified_html)

    print("\n--- Content Preview ---")
    content_preview = perception_module._get_content_preview(sample_html)
    print(content_preview)

