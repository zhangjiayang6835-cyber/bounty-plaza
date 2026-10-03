<content>
import { TextDocument } from 'vscode-languageserver-textdocument';
import { SassParser } from './parser/sass-parser';
import { SassCompiler } from './compiler/sass-compiler';
import { SassDiagnostics } from './diagnostics/sass-diagnostics';
import { SassCompletion } from './completion/sass-completion';
import { SassHover } from './hover/sass-hover';
import { SassDefinition } from './definition/sass-definition';
import { SassSymbols } from './symbols/sass-symbols';
import { SassReferences } from './references/sass-references';
import { SassDocumentHighlight } from './document-highlight/sass-document-highlight';
import { SassFormatting } from './formatting/sass-formatting';

export class SassLanguageService {
  private parser: SassParser;
  private compiler: SassCompiler;
  private diagnostics: SassDiagnostics;
  private completion: SassCompletion;
  private hover: SassHover;
  private definition: SassDefinition;
  private symbols: SassSymbols;
  private references: SassReferences;
  private documentHighlight: SassDocumentHighlight;
  private formatting: SassFormatting;

  constructor() {
    this.parser = new SassParser();
    this.compiler = new SassCompiler();
    this.diagnostics = new SassDiagnostics();
    this.completion = new SassCompletion();
    this.hover = new SassHover();
    this.definition = new SassDefinition();
    this.symbols = new SassSymbols();
    this.references = new SassReferences();
    this.documentHighlight = new SassDocumentHighlight();
    this.formatting = new SassFormatting();
  }

  public async compileSass(sassCode: string): Promise<string> {
    return this.compiler.compile(sassCode);
  }

  public async getVariables(document: TextDocument) {
    return this.parser.parseVariables(document.getText());
  }

  public async getMixins(document: TextDocument) {
    return this.parser.parseMixins(document.getText());
  }

  public async getFunctions(document: TextDocument) {
    return this.parser.parseFunctions(document.getText());
  }

  public getDiagnostics() {
    return this.diagnostics;
  }

  public getCompletion() {
    return this.completion;
  }

  public getHover() {
    return this.hover;
  }

  public getDefinition() {
    return this.definition;
  }

  public getSymbols() {
    return this.symbols;
  }

  public getReferences() {
    return this.references;
  }

  public getDocumentHighlight() {
    return this.documentHighlight;
  }

  public getFormatting() {
    return this.formatting;
  }
}