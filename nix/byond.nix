{ lib
, stdenvNoCC
, fetchurl
, makeWrapper
, icoutils
, wineWowPackages
, winePackage ? wineWowPackages.stable
, winetricks
, bubblewrap
, cabextract
, p7zip
, samba
, gnused
, coreutils
, findutils
, util-linux
, procps
, bash
}:

let
  version = "516.1680";
  wine = winePackage;

  byondInstaller = fetchurl {
    url = "https://www.byond.com/download/build/516/516.1680_byond.exe";
    hash = "sha256-4EE2IMGLqQ4TV6gmcSs3+Tl508pNuTs/d+UbcMfbYkE=";
  };

  webview2Installer = fetchurl {
    url = "https://go.microsoft.com/fwlink/?linkid=2124701";
    name = "MicrosoftEdgeWebView2RuntimeInstallerX64.exe";
    hash = "sha256-rxBn2cx/EHypbd2NUhJyS9rjvZ60bmGdLKXB8+MEFhI=";
  };

  runtimePath = lib.makeBinPath [
    wine
    winetricks
    bubblewrap
    cabextract
    p7zip
    samba
    gnused
    coreutils
    findutils
    util-linux
    procps
    bash
  ];

in
stdenvNoCC.mkDerivation {
  pname = "byond-dreamseeker";
  inherit version;

  dontUnpack = true;

  nativeBuildInputs = [ makeWrapper icoutils ];

  installPhase = ''
    runHook preInstall

    mkdir -p $out/bin $out/share/byond $out/share/applications $out/share/icons/hicolor/256x256/apps

    cp ${byondInstaller} $out/share/byond/byond_installer.exe
    cp ${webview2Installer} $out/share/byond/webview2_installer.exe

    cat > $out/bin/dreamseeker << 'EOF'
    #!/usr/bin/env bash
    set -euo pipefail
    export WINEPREFIX="''${WINEPREFIX:-$HOME/.byond-wine}"
    export PATH="${runtimePath}:$PATH"

    if [ ! -d "$WINEPREFIX" ]; then
      echo "Initializing Wine prefix for BYOND at $WINEPREFIX..."
      wineboot -i
    fi

    exec wine "$@"
    EOF

    chmod +x $out/bin/dreamseeker

    runHook postInstall
  '';

  meta = with lib; {
    description = "BYOND Dream Seeker runner and installer wrapper for /tg/station";
    homepage = "https://www.byond.com/";
    license = licenses.unfree;
    platforms = [ "x86_64-linux" ];
    maintainers = [ "zhangjiayang6835-cyber" "wiliancolomboo-tech" ];
  };
}
