<?php

class TestClass1
{
    // Single quotes
    private $_xpath1 = '//a/table';

    // Double quotes
    private $_xpath2 = "//a[@class='test']";

    // Test xpaths inside a method
    public function someMethod()
    {
        $xpath3 = '//table/tr';

        $xpathTmp = $this->_xpath1;

        $this->getXpathCount($xpathTmp);

        $this->click->('//input//a');

        $this->type("//div//$xpathTmp");

        $this->click->("//div[@class='test']");

        $this->select->('xpath=\'//div\'');

        $this->select->("xpath=//span");

        $xpathAssignment = '//div/table';
        $var = "//div$xpathAssignment";

        $xpathAssignment2 = '//div/table';
        $var = $xpathAssignment2 . '//div';

        $xpathAssignment3 = '//div/table';
        $var = '//div' . $xpathAssignment3;
    }

}
