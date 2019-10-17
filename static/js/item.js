var userlist= document.getElementById("userlist"),
item= document.getElementById("item"),

bank= document.getElementById("bank"),
bankTitle= document.getElementById("bankTitle"),
bankContainer= document.getElementById("bankContainer"),

inventory= document.getElementById("inventory"),
inventoryTitle= document.getElementById("inventoryTitle"),
inventoryContainer= document.getElementById("inventoryContainer"),

showInventory=true,
showBank=true;

class itemHandler {

        adjustUserlistHeight=()=>{
            userlist.style.height=`calc(100% - ${item.offsetHeight}px)`
        }

        ////
        displayBank=()=>{

            if(showBank)bankContainer.style.display="block";
            else bankContainer.style.display="none";
            this.adjustUserlistHeight();
        }

        displayInventory=()=>{
            if(showInventory)inventoryContainer.style.display="block";
            else inventoryContainer.style.display="none";
            this.adjustUserlistHeight();
        }

        RefreshItemBank=(items)=>{

            bankContainer.removeChild();
            for(let a=0;a>items.length;a++){

                let divimg = document.createElement("div"); 
                let img = document.createElement("img"); 
                img.src="/img/inventory/"+items[a]+".gif";
                divimg.appendChild(img);
                bankContainer.appendChild(divimg);
            }
                this.adjustUserlistHeight();

        }   

        RefreshtemInv=(items)=>{
            inventoryContainer.removeChild();
            for(let a=0;a>items.length;a++){
                let divimg = document.createElement("div"); 
                let img = document.createElement("img"); 
                img.src="/img/inventory/"+items[a]+".gif";
                divimg.appendChild(img);
                inventoryContainer.appendChild(divimg);
    
            }
            this.adjustUserlistHeight();

        }

        initItem=()=>{
            ////---> search a cookie  if display or not 
            this.adjustUserlistHeight();

            //onclick Display true or false
            bankTitle.addEventListener("click", ()=>{
                showBank=!showBank;
                this.displayBank();
                this.adjustUserlistHeight();

            });

            inventoryTitle.addEventListener("click", ()=>{
                showInventory=!showInventory;
                this.displayInventory();
                this.adjustUserlistHeight();

            });

            //refresh each 1s bank and inventory
            

            }
}
