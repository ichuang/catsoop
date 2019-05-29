cs_auth_required = False
cs_long_name = "CAT-SOOP Website"

TOR_STRING = lambda n: ("torsocks %s" % n) if "onion" in cs_url_root else n

cs_footer = (
    """<a href="http://creativecommons.org/licenses/by-sa/4.0/" rel="license"><img alt="Creative Commons License" src="COURSE/cc-by-sa.png" style="border-width:0"></a><br/>The contents of this page are Copyright &copy; 2016-2019 by the CAT-SOOP Developers.<br/>They are licensed under a <a rel="license" href="http://creativecommons.org/licenses/by-sa/4.0/">Creative Commons Attribution-ShareAlike 4.0 International License</a>.<br/>The original form of this web site is source code in the CAT-SOOP specification
format.<br/>The source code is available in the Mercurial repository at  <a href="/hg/catsoop">%s/hg/catsoop</a>.<br/><hr width="300" style="background-color:#000000;border-color:#000000" />"""
    % cs_url_root
)
