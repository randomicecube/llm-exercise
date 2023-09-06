{
  inputs = {
    nixpkgs.url = "flake:nixpkgs";
    mach-nix.url = "flake:mach-nix";
  };

  outputs = { self, nixpkgs, mach-nix }:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs { inherit system; };
      machNix = mach-nix.lib."${system}";
      myPython = machNix.mkPython {
        requirements = ''
          transformers
        '';
      };
    in {
      devShell.x86_64-linux = pkgs.mkShell {
        buildInputs = [
          myPython
        ];
      };
    };
}