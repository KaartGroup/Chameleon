import styled from "styled-components";

export const Wrapper = styled.div`
    display: flex;
    border-bottom: 2px solid #f4753c;
    border-top: 2px solid #f4753c;
    background-color: white;
    border-radius: 6px;
    box-shadow: 0px 2px;
    // box-shadow-color: #f4753c;
    transform:translate(0%, 80%)
`;

export const Heading = styled.p`
    display: flex;
    font-family: "Hind Guntur",sans-serif;
    width: 100%;
    font-size: 20px;
    font-weight: bold;
    justify-content: center;
    align-items: center;
`;

export const WhenInput = styled.input`
  width: 80%;
  padding: 12px 20px;
  margin: 8px 0;
  display: inline-block;
  border: 1px solid #ccc;
  border-radius: 6px;
  box-sizing: border-box;
`;

export const FormWrapper = styled.div`
display: grid;
justify-content: center;
align-items: center;
transform:translate(0%, 80%)
`;

export const Label = styled.p`
font-size: 15px;
`;

export const Calander = styled.img`
height: 24px;
padding: 1%; 
color: white;
`;