const DEFAULT_LANGUAGE = 'en';
const DEFAULT_TARGET = 'World';
const DEFAULT_PUNCTUATION = '!';

const FORMATS = Object.freeze({
  TEXT: 'text',
  JSON: 'json',
  MARKDOWN: 'markdown',
  HTML: 'html',
  ANSI: 'ansi',
  ASCII_BANNER: 'ascii_banner'
});

const GREETINGS = Object.freeze({
  en: 'Hello',
  zh: '你好',
  es: 'Hola',
  fr: 'Bonjour',
  de: 'Hallo',
  ja: 'こんにちは',
  ko: '안녕하세요',
  ru: 'Привет',
  ar: 'مرحبا',
  hi: 'नमस्ते',
  pt: 'Olá',
  it: 'Ciao',
  nl: 'Hallo',
  tr: 'Merhaba',
  pl: 'Cześć',
  sv: 'Hej',
  el: 'Γεια σας',
  vi: 'Xin chào',
  id: 'Halo',
  sw: 'Jambo'
});

/**
 * Enterprise Hello World engine providing multilingual greetings and multi-format rendering.
 */
class HelloWorld {
  /**
   * Initializes the HelloWorld instance.
   * @param {Object} config - Initial configuration.
   */
  constructor(config = {}) {
    this.defaultLanguage = config.defaultLanguage || DEFAULT_LANGUAGE;
    this.defaultTarget = config.defaultTarget || DEFAULT_TARGET;
    this.languages = { ...GREETINGS, ...(config.customGreetings || {}) };
  }

  /**
   * Retrieves the list of supported ISO language codes.
   * @returns {string[]} Array of supported language codes.
   */
  getSupportedLanguages() {
    return Object.keys(this.languages).sort();
  }

  /**
   * Registers or overrides a language greeting.
   * @param {string} code - ISO language code.
   * @param {string} greeting - Greeting word.
   */
  registerLanguage(code, greeting) {
    if (!code || typeof code !== 'string') {
      throw new TypeError('Language code must be a non-empty string');
    }
    if (!greeting || typeof greeting !== 'string') {
      throw new TypeError('Greeting must be a non-empty string');
    }
    this.languages[code.toLowerCase()] = greeting;
  }

  /**
   * Builds an ASCII box banner enclosing the greeting text.
   * @param {string} text - Message text.
   * @returns {string} Multiline ASCII banner.
   */
  renderAsciiBanner(text) {
    const pad = 2;
    const innerWidth = text.length + pad * 2;
    const top = '+' + '-'.repeat(innerWidth) + '+';
    const empty = '|' + ' '.repeat(innerWidth) + '|';
    const middle = '|' + ' '.repeat(pad) + text + ' '.repeat(pad) + '|';
    return [top, empty, middle, empty, top].join('\n');
  }

  /**
   * Generates a greeting based on specified options.
   * @param {Object} options - Greeting parameters.
   * @param {string} [options.target] - Recipient name.
   * @param {string} [options.language] - Language code.
   * @param {string} [options.punctuation] - Punctuation mark.
   * @param {boolean} [options.shout] - Whether to uppercase the message.
   * @param {string} [options.format] - Output format: text, json, markdown, html, ansi, ascii_banner.
   * @returns {string} Formatted greeting output.
   */
  greet(options = {}) {
    const langCode = (options.language || this.defaultLanguage).toLowerCase();
    const greetingWord = this.languages[langCode] || this.languages[DEFAULT_LANGUAGE];
    const target = options.target !== undefined && options.target !== null && String(options.target).trim() !== ''
      ? String(options.target).trim()
      : this.defaultTarget;
    const punct = options.punctuation !== undefined && options.punctuation !== null
      ? String(options.punctuation)
      : DEFAULT_PUNCTUATION;

    let message = `${greetingWord}, ${target}${punct}`;
    if (options.shout) {
      message = message.toUpperCase();
    }

    const format = (options.format || FORMATS.TEXT).toLowerCase();
    switch (format) {
      case FORMATS.JSON:
        return JSON.stringify({
          greeting: greetingWord,
          target,
          punctuation: punct,
          message,
          language: langCode,
          shout: Boolean(options.shout)
        }, null, 2);

      case FORMATS.MARKDOWN:
        return `# ${message}`;

      case FORMATS.HTML:
        return `<div class="greeting"><h1>${message}</h1></div>`;

      case FORMATS.ANSI:
        return `\x1b[1;32m${message}\x1b[0m`;

      case FORMATS.ASCII_BANNER:
        return this.renderAsciiBanner(message);

      case FORMATS.TEXT:
      default:
        return message;
    }
  }

  /**
   * Parses CLI flags into greeting options.
   * @param {string[]} argv - Array of argument strings.
   * @returns {Object} Parsed options object.
   */
  parseCliArgs(argv = []) {
    const options = {
      target: undefined,
      language: undefined,
      punctuation: undefined,
      shout: false,
      format: FORMATS.TEXT,
      help: false,
      version: false
    };

    for (let i = 0; i < argv.length; i += 1) {
      const arg = argv[i];
      if (arg === '--target' || arg === '-t') {
        options.target = argv[i + 1];
        i += 1;
      } else if (arg.startsWith('--target=')) {
        options.target = arg.slice('--target='.length);
      } else if (arg === '--lang' || arg === '-l') {
        options.language = argv[i + 1];
        i += 1;
      } else if (arg.startsWith('--lang=')) {
        options.language = arg.slice('--lang='.length);
      } else if (arg === '--punct' || arg === '-p') {
        options.punctuation = argv[i + 1];
        i += 1;
      } else if (arg.startsWith('--punct=')) {
        options.punctuation = arg.slice('--punct='.length);
      } else if (arg === '--format' || arg === '-f') {
        options.format = argv[i + 1];
        i += 1;
      } else if (arg.startsWith('--format=')) {
        options.format = arg.slice('--format='.length);
      } else if (arg === '--json') {
        options.format = FORMATS.JSON;
      } else if (arg === '--shout' || arg === '-s') {
        options.shout = true;
      } else if (arg === '--help' || arg === '-h') {
        options.help = true;
      } else if (arg === '--version' || arg === '-v') {
        options.version = true;
      } else if (!arg.startsWith('-') && options.target === undefined) {
        options.target = arg;
      }
    }
    return options;
  }

  /**
   * Executes the CLI workflow.
   * @param {string[]} argv - Command-line arguments.
   * @param {NodeJS.WriteStream} [outputStream] - Target output stream.
   * @returns {number} Exit status code.
   */
  runCli(argv = process.argv.slice(2), outputStream = process.stdout) {
    const options = this.parseCliArgs(argv);
    if (options.help) {
      const helpText = [
        'Usage: hello_world [target] [options]',
        '',
        'Options:',
        '  -t, --target <name>      Recipient name (default: World)',
        '  -l, --lang <code>        Language ISO code (default: en)',
        '  -f, --format <type>      Output format: text, json, markdown, html, ansi, ascii_banner',
        '  -p, --punct <mark>       Punctuation mark (default: !)',
        '  -s, --shout              Convert message to uppercase',
        '      --json               Shorthand for --format json',
        '  -v, --version            Display version information',
        '  -h, --help               Show this help message'
      ].join('\n');
      outputStream.write(helpText + '\n');
      return 0;
    }

    if (options.version) {
      outputStream.write('bounty-plaza-hello-world 1.0.0\n');
      return 0;
    }

    const output = this.greet(options);
    outputStream.write(output + '\n');
    return 0;
  }
}

const defaultInstance = new HelloWorld();

module.exports = {
  HelloWorld,
  FORMATS,
  GREETINGS,
  DEFAULT_LANGUAGE,
  DEFAULT_TARGET,
  DEFAULT_PUNCTUATION,
  defaultInstance,
  greet: (options) => defaultInstance.greet(options)
};

if (require.main === module) {
  defaultInstance.runCli(process.argv.slice(2));
}
