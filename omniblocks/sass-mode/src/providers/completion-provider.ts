<content>
import { TextDocument, Position, CompletionItem, CompletionItemKind } from 'vscode-languageserver-textdocument';
import { SassLanguageService } from '../sass-language-service';

export class SassCompletionProvider {
  private languageService: SassLanguageService;

  constructor(languageService: SassLanguageService) {
    this.languageService = languageService;
  }

  public async provideCompletionItems(document: TextDocument, position: Position): Promise<CompletionItem[]> {
    const text = document.getText();
    const line = document.lineAt(position.line).text;
    const linePrefix = line.substring(0, position.character);
    
    const items: CompletionItem[] = [];
    
    // Variable completions
    if (linePrefix.endsWith('$')) {
      const variables = await this.languageService.getVariables(document);
      variables.forEach(variable => {
        items.push({
          label: `$${variable.name}`,
          kind: CompletionItemKind.Variable,
          detail: `Variable: ${variable.value}`,
          documentation: `SASS variable: ${variable.name} = ${variable.value}`
        });
      });
    }
    
    // Mixin completions
    if (linePrefix.includes('@include ')) {
      const mixins = await this.languageService.getMixins(document);
      mixins.forEach(mixin => {
        items.push({
          label: `@include ${mixin.name}(...)`,
          kind: CompletionItemKind.Function,
          detail: `Mixin: ${mixin.name}(${mixin.parameters.join(', ')})`,
          documentation: `SASS mixin: ${mixin.name}(${mixin.parameters.join(', ')})`
        });
      });
    }
    
    // Function completions
    if (linePrefix.includes('(') && !linePrefix.includes('@function')) {
      const functions = await this.languageService.getFunctions(document);
      functions.forEach(func => {
        items.push({
          label: `${func.name}(...)`,
          kind: CompletionItemKind.Function,
          detail: `Function: ${func.name}(${func.parameters.join(', ')})`,
          documentation: `SASS function: ${func.name}(${func.parameters.join(', ')})`
        });
      });
    }
    
    // CSS property completions
    const cssProperties = [
      'color', 'background-color', 'font-size', 'font-family', 'margin', 'padding',
      'display', 'position', 'top', 'left', 'width', 'height', 'border', 'border-radius',
      'text-align', 'line-height', 'opacity', 'z-index', 'float', 'clear', 'overflow',
      'box-shadow', 'text-shadow', 'transition', 'transform', 'animation', 'cursor',
      'outline', 'visibility', 'flex', 'grid', 'content', 'align-items', 'justify-content'
    ];
    
    cssProperties.forEach(property => {
      items.push({
        label: property,
        kind: CompletionItemKind.Property,
        documentation: `CSS property: ${property}`
      });
    });
    
    // Color completions
    const colors = [
      'red', 'green', 'blue', 'yellow', 'orange', 'purple', 'pink', 'brown',
      'black', 'white', 'gray', 'lightgray', 'darkgray', 'transparent'
    ];
    
    colors.forEach(color => {
      items.push({
        label: color,
        kind: CompletionItemKind.Color,
        documentation: `Color: ${color}`
      });
    });
    
    // Unit completions
    const units = ['px', 'em', 'rem', '%', 'vh', 'vw', 'deg', 's', 'ms'];
    
    units.forEach(unit => {
      items.push({
        label: unit,
        kind: CompletionItemKind.Unit,
        documentation: `Unit: ${unit}`
      });
    });
    
    return items;
  }
}