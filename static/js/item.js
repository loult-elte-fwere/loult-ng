
var userlist= document.getElementById("userlist");
var item= document.getElementById("item");

var bank= document.getElementById("bank");
var bankTitle= document.getElementById("bankTitle");
var bankContainer= document.getElementById("bankContainer");

var inventory= document.getElementById("inventory");
var inventoryTitle= document.getElementById("inventoryTitle");
var inventoryContainer= document.getElementById("inventoryContainer");

var showInventory=true;
var showBank=true;

    adjustUserlistHeight=()=>{
        userlist.style.height=`calc(100% - ${item.offsetHeight}px)`
    }

    ////
    displayBank=()=>{

        if(showBank)bankContainer.style.display="block";
        else bankContainer.style.display="none";
        adjustUserlistHeight();
    }
    displayInventory=()=>{
        if(showInventory)inventoryContainer.style.display="block";
        else inventoryContainer.style.display="none";
        adjustUserlistHeight();
    }

addItemBank=(item)=>{

}
addItemInv=(item)=>{

}

document.addEventListener('DOMContentLoaded', function(){

    //////setup
    ////---> search a cookie  if display or not 
    adjustUserlistHeight();

    //onclick Display true or false
    bankTitle.addEventListener("click", ()=>{
        showBank=!showBank;
        displayBank();
    });

    inventoryTitle.addEventListener("click", ()=>{
        showInventory=!showInventory;
        displayInventory();
    });


}, false);

