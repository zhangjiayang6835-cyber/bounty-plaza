import React, { useState, useEffect } from 'react';
import { Terminal } from 'xterm';
import { FitAddon } from 'xterm-addon-fit';
import 'xterm/css/xterm.css';

const LinuxEmulator = () => {
  const terminalRef = useRef(null);
  const [terminal, setTerminal] = useState(null);
  const [fitAddon, setFitAddon] = useState(null);

  useEffect(() => {
    if (terminalRef.current) {
      const newTerminal = new Terminal({
        cursorBlink: true,
        theme: {
          background: '#073642',
          foreground: '#839496',
        },
      });
      
      const newFitAddon = new FitAddon();
      newTerminal.loadAddon(newFitAddon);
      
      newTerminal.open(terminalRef.current);
      newFitAddon.fit();
      
      setTerminal(newTerminal);
      setFitAddon(newFitAddon);
      
      // Initialize with Linux-like prompt
      newTerminal.write('\r\nWelcome to OmniBlocks Linux Emulator\r\n');
      newTerminal.write('user@omniblocks:~$ ');
      
      // Handle terminal input
      newTerminal.onData((data) => {
        newTerminal.write(data);
      });
      
      // Handle terminal resize
      const handleResize = () => {
        newFitAddon.fit();
      };
      
      window.addEventListener('resize', handleResize);
      
      return () => {
        newTerminal.dispose();
        window.removeEventListener('resize', handleResize);
      };
    }
  }, []);

  return (
    <div className="linux-emulator" style={{ width: '100%', height: '100%' }}>
      <div ref={terminalRef} className="terminal-container" />
    </div>
  );
};

export default LinuxEmulator;