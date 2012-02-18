<?php

class TestClass1
{
    // Single quotes
    private $_xpath1 = '//a/table';

    // Double quotes
    private $_xpath2 = "css=a.test";

    // Test xpaths inside a method
    public function someMethod()
    {
        $xpath3 = '//table/tr';

        $xpathTmp = $this->_xpath1;

        $this->getXpathCount($xpathTmp);

        $this->click->('css=input a');

        $this->type("//div//$xpathTmp");

        $this->click->("css=div.test");

        $this->select->('xpath=\'//div\'');

        $this->select->("xpath=//span");
    }

}
