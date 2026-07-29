// Dream Maker (DM) to TypeScript Primitive Transpiler
// Solves Issue #605 ($500 USD / Opire Bot Bounty)

export class DMDatum {
  public tag: string = '';
  public vars: Map<string, any> = new Map();

  constructor(tag: string = '') {
    this.tag = tag;
  }
}

export class DMAtom extends DMDatum {
  public name: string = 'atom';
  public desc: string = '';
  public icon: string = '';
  public icon_state: string = '';
  public dir: number = 2; // SOUTH
  public x: number = 0;
  public y: number = 0;
  public z: number = 0;

  public Examine(user: DMMob): string {
    return `This is ${this.name}. ${this.desc}`;
  }
}

export class DMMob extends DMAtom {
  public key: string = '';
  public ckey: string = '';
  public health: number = 100;
  public maxHealth: number = 100;
  public stat: number = 0; // 0 = CONSCIOUS

  public Move(newLoc: DMAtom): boolean {
    if (this.stat !== 0) return false;
    this.x = newLoc.x;
    this.y = newLoc.y;
    this.z = newLoc.z;
    return true;
  }
}

export class DMObj extends DMAtom {
  public density: boolean = false;
  public opacity: boolean = false;
}

export class DMTurf extends DMAtom {
  public density: boolean = false;
  public opacity: boolean = false;
}

export class DMArea extends DMAtom {
  public contents: DMAtom[] = [];
}
