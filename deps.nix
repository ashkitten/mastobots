with import <nixpkgs> {};

( let
    mastodonpy = python36.pkgs.buildPythonPackage rec {
      pname = "Mastodon.py";
      version = "1.2.2";

      src = python36.pkgs.fetchPypi {
        inherit pname version;
        sha256 = "ca3db745a07d74c985cdeeee7c3937bf8b389aef69b89d66c7ddcfed8ffbffeb";
      };

      doCheck = false;
      propagatedBuildInputs = with python36Packages; [ decorator pytz six dateutil requests ];

      meta = {
        homepage = "https://github.com/halcy/Mastodon.py";
        description = "Python wrapper for the Mastodon API";
      };
    };

    ananas = python36.pkgs.buildPythonPackage rec {
      pname = "ananas";
      version = "1.0.0b5";

      src = python36.pkgs.fetchPypi {
        inherit pname version;
        sha256 = "45131c5ecb268a73d83e934c5dfea44f33571ce4b28c6d6df7ea32c407d210df";
      };

      doCheck = false;
      propagatedBuildInputs = with python36Packages; [ requests more-itertools mastodonpy ];

      meta = {
        description = " The Python Bot Framework for Mastodon";
        homepage = "https://github.com/chronister/ananas";
      };
    };

    markovify = python36.pkgs.buildPythonPackage rec {
      pname = "markovify";
      version = "0.7.1";

      src = python36.pkgs.fetchPypi {
        inherit pname version;
        sha256 = "f016ef58f60a8afb925aa16803538561c4b00375bf0b7f84952c29993805b9a7";
      };

      doCheck = false;
      propagatedBuildInputs = with python36Packages; [ unidecode ];

      meta = {
        description = " The Python Bot Framework for Mastodon";
        homepage = "https://github.com/chronister/ananas";
      };
    };

  in python36.withPackages (ps: [ ananas markovify ])
).env
