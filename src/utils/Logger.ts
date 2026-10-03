/**
 * Logger - Simple logging utility
 * 
 * Provides a consistent way to log messages throughout the codebase.
 */

export class Logger {
  private readonly name: string;

  constructor(name: string) {
    this.name = name;
  }

  public info(message: string, ...args: any[]): void {
    console.log(`[${this.name}] INFO: ${message}`, ...args);
  }

  public warn(message: string, ...args: any[]): void {
    console.warn(`[${this.name}] WARN: ${message}`, ...args);
  }

  public error(message: string, ...args: any[]): void {
    console.error(`[${this.name}] ERROR: ${message}`, ...args);
  }
}