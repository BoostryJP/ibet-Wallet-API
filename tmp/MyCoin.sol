pragma solidity ^0.4.19;
contract MyToken {
  string public name;
  string public symbol;
  uint8 public decimals;
  uint256 public totalSupply;
  mapping (address => uint256) public balanceOf;

  event Transfer(address indexed from, address indexed to, uint256 value);
  event Issue(address indexed sender, uint256 value);

  function MyToken(uint256 _supply, string _name, string _symbol, uint8 _decimals) public {
    balanceOf[msg.sender] = _supply;
    name = _name;
    symbol = _symbol;
    decimals = _decimals;
    totalSupply = _supply;

    Issue(msg.sender, _supply);
  }

  function transfer(address _to, uint256 _value) public {
    require(balanceOf[msg.sender] > _value) ;
    require(balanceOf[_to] + _value > balanceOf[_to]) ;

    balanceOf[msg.sender] -= _value;
    balanceOf[_to] += _value;

    Transfer(msg.sender, _to, _value);
  }

  function getBalanceOf(address _owner) public constant returns (uint256){
      return balanceOf[_owner];
  }

}
