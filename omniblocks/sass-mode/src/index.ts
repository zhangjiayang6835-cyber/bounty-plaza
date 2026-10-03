<content>
import { TextDocument, Position, Range } from 'vscode-languageserver-textdocument';
import { SassLanguageService } from './sass-language-service';
import { SassCompletionProvider } from './providers/completion-provider';
import { SassHoverProvider } from './providers/hover-provider';
import { SassDefinitionProvider } from './providers/definition-provider';
import { SassDocumentSymbolProvider } from './providers/document-symbol-provider';
import { SassWorkspaceSymbolProvider } from './providers/workspace-symbol-provider';
import { SassReferencesProvider } from './providers/references-provider';
import { SassDocumentHighlightProvider } from './providers/document-highlight-provider';
import { SassFormattingProvider } from './providers/formatting-provider';
import { SassDiagnosticsProvider } from './providers/diagnostics-provider';

export class SassMode {
  private languageService: SassLanguageService;
  private completionProvider: SassCompletionProvider;
  private hoverProvider: SassHoverProvider;
  private definitionProvider: SassDefinitionProvider;
  private documentSymbolProvider: SassDocumentSymbolProvider;
  private workspaceSymbolProvider: SassWorkspaceSymbolProvider;
  private referencesProvider: SassReferencesProvider;
  private documentHighlightProvider: SassDocumentHighlightProvider;
  private formattingProvider: SassFormattingProvider;
  private diagnosticsProvider: SassDiagnosticsProvider;

  constructor() {
    this.languageService = new SassLanguageService();
    this.completionProvider = new SassCompletionProvider(this.languageService);
    this.hoverProvider = new SassHoverProvider(this.languageService);
    this.definitionProvider = new SassDefinitionProvider(this.languageService);
    this.documentSymbolProvider = new SassDocumentSymbolProvider(this.languageService);
    this.workspaceSymbolProvider = new SassWorkspaceSymbolProvider(this.languageService);
    this.referencesProvider = new SassReferencesProvider(this.languageService);
    this.documentHighlightProvider = new SassDocumentHighlightProvider(this.languageService);
    this.formattingProvider = new SassFormattingProvider(this.languageService);
    this.diagnosticsProvider = new SassDiagnosticsProvider(this.languageService);
  }

  public getCompletionProvider() {
    return this.completionProvider;
  }

  public getHoverProvider() {
    return this.hoverProvider;
  }

  public getDefinitionProvider() {
    return this.definitionProvider;
  }

  public getDocumentSymbolProvider() {
    return this.documentSymbolProvider;
  }

  public getWorkspaceSymbolProvider() {
    return this.workspaceSymbolProvider;
  }

  public getReferencesProvider() {
    return this.referencesProvider;
  }

  public getDocumentHighlightProvider() {
    return this.documentHighlightProvider;
  }

  public getFormattingProvider() {
    return this.formattingProvider;
  }

  public getDiagnosticsProvider() {
    return this.diagnosticsProvider;
  }

  public async compileSass(document: TextDocument): Promise<string> {
    return this.languageService.compileSass(document.getText());
  }

  public async getVariables(document: TextDocument) {
    return this.languageService.getVariables(document);
  }

  public async getMixins(document: TextDocument) {
    return this.languageService.getMixins(document);
  }

  public async getFunctions(document: TextDocument) {
    return this.languageService.getFunctions(document);
  }
}