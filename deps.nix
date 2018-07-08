with import <nixpkgs> {};

let
  http-ece = python36.pkgs.buildPythonPackage rec {
    pname = "http-ece";
    version = "1.0.5";

    src = python36.pkgs.fetchPypi {
      pname = "http_ece";
      inherit version;
      sha256 = "2f31a0640c31a0c2934ab1e37005dd9a559ae854a16304f9b839e062074106cc";
    };

    doCheck = false;
    propagatedBuildInputs = with python36Packages; [ cryptography ];

    meta = {
      description = "A simple implementation of the encrypted content-encoding";
      homepage = "https://github.com/web-push-libs/encrypted-content-encoding";
    };
  };

  mastodonpy = python36.pkgs.buildPythonPackage rec {
    pname = "Mastodon.py";
    version = "1.3.0";

    src = python36.pkgs.fetchPypi {
      inherit pname version;
      sha256 = "339a60c4ea505dd5b6c8f6ac076ce40f9e7bdfcd72d9466869da8bf631e4b9f5";
    };

    doCheck = false;
    propagatedBuildInputs = with python36Packages; [ decorator pytz six dateutil requests http-ece ];

    meta = {
      description = "Python wrapper for the Mastodon API";
      homepage = "https://github.com/halcy/Mastodon.py";
    };
  };

  ananas = python36.pkgs.buildPythonPackage rec {
    pname = "ananas";
    version = "master";

    src = fetchFromGitHub {
      owner = "chr-1x";
      repo = "ananas";
      rev = "6100d97368c2053a0517ee80bff55eee2fdfa314";
      sha256 = "10lxlmd7k1vjh5p01w5ddl872cc6bc4mkd8qq80rihqv1l5dyzcx";
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

in stdenv.mkDerivation {
  name = "env";
  buildInputs = [
    ananas
    markovify
    espeak
    ffmpeg
  ];
}
