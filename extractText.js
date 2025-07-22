function extractAndPrintContent() {

    const getCleanedBody = () => {
        const bodyClone = document.body.cloneNode(true);
        const selectorsToRemove = [
            'header', 
            'footer', 
            'nav', 
            'aside', 
            'script', 
            'style', 
            'noscript', 
            'iframe', 
            'form',
            '[role="navigation"]',
            '[role="banner"]',
            '[role="complementary"]',
            '[role="contentinfo"]',
            '.header',
            '.footer',
            '#header',
            '#footer'
        ];

        bodyClone.querySelectorAll(selectorsToRemove.join(',')).forEach(el => el.remove());
        return bodyClone;
    };

    const findMainContent = (container) => {
        const mainSelectors = ['article', 'main', '.post', '#content', '#main', '.main'];
        let mainContent = null;

        for (const selector of mainSelectors) {
            mainContent = container.querySelector(selector);
            if (mainContent) break;
        }

        return mainContent || container;
    };

    try {
        const cleanedBody = getCleanedBody();
        const mainContentElement = findMainContent(cleanedBody);
        
        let textContent = mainContentElement.innerText || '';
        textContent = textContent.replace(/^\s*[\r\n]/gm, '').trim();

        if (!textContent) {
            console.error("Could not extract relevant content.");
            return;
        }

        const pageTitle = document.title || 'Current Page';
        
        console.log(`\n\n--- EXTRACTED CONTENT FROM: ${pageTitle} ---\n`);
        console.log(textContent);
        console.log("\n--- END OF CONTENT ---\n\n");

    } catch (error) {
        console.error("An error occurred during extraction:", error);
    }
}

extractAndPrintContent();