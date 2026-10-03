<content>
import { compileString } from 'sass';

export class SassCompiler {
  public async compile(sassCode: string, options?: any): Promise<string> {
    try {
      const result = compileString(sassCode, {
        sourceMap: true,
        ...options
      });
      
      return result.css;
    } catch (error) {
      console.error('SASS compilation error:', error);
      throw error;
    }
  }

  public async compileAsync(sassCode: string, options?: any): Promise<string> {
    try {
      const result = await compileStringAsync(sassCode, {
        sourceMap: true,
        ...options
      });
      
      return result.css;
    } catch (error) {
      console.error('SASS async compilation error:', error);
      throw error;
    }
  }

  public async compileWithSourceMap(sassCode: string, options?: any): Promise<{ css: string, sourceMap: any }> {
    try {
      const result = compileString(sassCode, {
        sourceMap: true,
        ...options
      });
      
      return {
        css: result.css,
        sourceMap: result.sourceMap
      };
    } catch (error) {
      console.error('SASS compilation with source map error:', error);
      throw error;
    }
  }
}