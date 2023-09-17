{
  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs";
    nixpkgs-unstable.url = "github:nixos/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { nixpkgs-unstable, flake-utils, ... }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs-unstable { inherit system; };
        pythonPackages = p: with p; [ huggingface-hub langchain ];
      in
      {
        devShell = pkgs.mkShell {
          buildInputs = with pkgs; [
            (python3.withPackages pythonPackages)
          ];
        };
      }
    );
}
