"""
Wrapper para manejar salida segura sin problemas de codificación
"""

def safe_print_global(text: str):
    """Global safe print function for use in enhanced_action_controller"""
    try:
        # Clean emojis and Unicode characters that cause encoding issues
        cleaned_text = text
        
        # Replace common problematic emojis and Unicode characters
        emoji_replacements = {
            '🎯': '[TARGET]',
            '🔧': '[TOOL]',
            '📡': '[SIGNAL]',
            '🔍': '[SEARCH]',
            '❌': '[ERROR]',
            '✅': '[SUCCESS]', 
            '⚠️': '[WARNING]',
            '🌐': '[WEB]',
            '📊': '[DATA]',
            '📁': '[FILE]',
            '🔄': '[RELOAD]',
            '⏳': '[WAIT]',
            '📜': '[SCROLL]',
            '🚀': '[START]',
            '💡': '[IDEA]',
            '🎉': '[COMPLETE]',
            '⏭️': '[SKIP]',
            '📋': '[LIST]'
        }
        
        for emoji, replacement in emoji_replacements.items():
            cleaned_text = cleaned_text.replace(emoji, replacement)
        
        # Remove any remaining problematic Unicode characters
        cleaned_text = cleaned_text.encode('ascii', 'replace').decode('ascii')
        print(cleaned_text)
        
    except Exception:
        print("[Message with encoding issues - unable to display]")
