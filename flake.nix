{
  description = "SS13 /tg/station Nix flake with agentic Wine + Xvfb screenshot harness and BYOND environment";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs {
          inherit system;
          config.allowUnfree = true;
        };

        version = "516.1680";

        byondPackage = pkgs.callPackage ./nix/byond.nix {
          winePackage = pkgs.wineWowPackages.staging;
        };

        screenshotHarness = pkgs.writeShellApplication {
          name = "ss13-screenshot-harness";
          runtimeInputs = with pkgs; [
            bash
            coreutils
            xorg.xorgserver       # provides Xvfb
            xorg.xwininfo
            xorg.xwd
            imagemagick           # provides import and convert
            xdotool
            wineWowPackages.staging
            python311
            python311Packages.pillow
          ];
          text = ''
            exec python3 "${./scripts/ss13_screenshot_harness.py}" "$@"
          '';
        };

      in
      {
        packages = {
          default = screenshotHarness;
          byond = byondPackage;
          harness = screenshotHarness;
        };

        apps = {
          default = flake-utils.lib.mkApp {
            drv = screenshotHarness;
          };
          screenshot = flake-utils.lib.mkApp {
            drv = screenshotHarness;
          };
        };

        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            wineWowPackages.staging
            winetricks
            xorg.xorgserver
            imagemagick
            xdotool
            git
            gh
            python311
            python311Packages.pytest
            python311Packages.pillow
          ];

          shellHook = ''
            echo "========================================================"
            echo "SS13 /tg/station Agentic Dev Shell (Wine + Xvfb) Loaded"
            echo "Run 'ss13-screenshot-harness --help' to test captures"
            echo "========================================================"
          '';
        };
      }
    );
}
