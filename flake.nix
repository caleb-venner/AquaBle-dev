{
  description = "Unified development environment for AquaBle (Backend & Frontend)";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  };

  outputs = { self, nixpkgs }:
    let
      supportedSystems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
      forAllSystems = nixpkgs.lib.genAttrs supportedSystems;
    in
    {
      devShells = forAllSystems (system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
        in
        {
          default = pkgs.mkShell {
        packages = with pkgs; [
          # Backend dependencies
          python313
          uv
          
          # Frontend dependencies
          nodejs_22
        ];

        shellHook = ''
          # Keep npm globally installed packages strictly local to the project
          export npm_config_prefix="$PWD/.npm-global"
          export PATH="$PWD/.npm-global/bin:$PWD/frontend/node_modules/.bin:$PATH"

          # Optional: Setup Python virtual environment automatically with uv if missing
          if [ ! -d ".venv" ]; then
            echo "Creating python virtual environment with uv..."
            uv venv
          fi
          
          echo " AquaBle Dev Environment Active"
          echo "- Python: $(python3 --version)"
          echo "- Node.js: $(node --version)"
          echo "- npm: $(npm --version)"
        '';
          };
        }
      );
    };
}
