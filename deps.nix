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
      version = "1.0.0b9";

      src = python36.pkgs.fetchPypi {
        inherit pname version;
        sha256 = "430149fcda7ee2cb156de9c3d10977fd6523ffbab6f6d16003f0b73c35b1bb61";
      };

      doCheck = false;
      propagatedBuildInputs = with python36Packages; [ requests more-itertools mastodonpy configobj ];

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
