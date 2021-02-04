import React, { useContext, useRef } from "react";
import { ChameleonContext } from "../../common/ChameleonContext";
import { Wrapper, Heading, Label, FormWrapper, HowInput, Button, Tag } from "./styles";
import tag from "../../images/tag.svg"; 
// TODO add history of favorite tags, make into buttons see old chameleon.kaart.com
export const How = () => {
    const tagRef = useRef();
    const selectRef = useRef();

    const { tags, setTags } = useContext(ChameleonContext);

    return (
        <>
            <Wrapper>
                <Heading> 
                 How<Tag src={tag} alt="tag IMG"/>
                </Heading>
            </Wrapper>
            <FormWrapper>
                <Label>
                    Tag:
                    <HowInput
                        type="text"
                        placeholder="OSM Tag"
                        ref={tagRef}
                    />
                    </Label>
                <Button onClick={(e) => { 
                    e.preventDefault();

                    let oldVals = [];
                    let newVal = tagRef.current.value;
                    let options = selectRef.current.options;
                    
                    for (var elm in options) {
                        if (typeof(options[elm]) == "object") {
                            oldVals.push(options[elm].value)
                        }
                    }

                    if (newVal !== "" && !oldVals.includes(newVal)) {
                        var option = document.createElement("option");

                        option.text = newVal;
                        selectRef.current.add(option);
                        setTags(tags.concat(newVal));
                        tagRef.current.value = "";
                    }
                }}>
                    Add
                </Button>
                <Button onClick={(e) => { 
                    e.preventDefault();

                    if (selectRef.current.selectedIndex === -1) {
                        selectRef.current.setCustomValidity("Please select a tag to remove");
                        selectRef.current.reportValidity();
                        selectRef.current.setCustomValidity("");
                        return;
                    }

                    // removes the selectedIndex's value from the state tags
                    // TODO readabilty
                    var index = tags.indexOf(selectRef.current.options[selectRef.current.selectedIndex].value);
                    tags.splice(index, 1);
                    selectRef.current.remove(selectRef.current.selectedIndex);
                    setTags(tags)

                }}>
                    Remove
                </Button>
                <Button onClick={(e) => { e.preventDefault(); selectRef.current.length = 0; setTags([]); }}>Clear</Button>
                <select size="5" multiple="" ref={selectRef} />
            </FormWrapper>
        </>
    );
};
