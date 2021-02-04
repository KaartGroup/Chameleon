import styled from "styled-components";

export const Wrapper = styled.div`
    display: flex;
    border-bottom: 2px solid #f4753c;
    background-color: white;
    border-radius: 6px;
    box-shadow: 0px 2px;
    // box-shadow-color: #f4753c;
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

export const FormWrapper = styled.div`
display: grid;
justify-content: center;
align-items: center;
`;

export const HowInput = styled.input`
  padding: 12px 20px;
  margin: 8px 8px;
  display: inline-block;
  border: 1px solid #ccc;
  border-radius: 6px;
  box-sizing: border-box;
`;

export const Label = styled.p`
font-size: 15px;
`;

export const Button = styled.button`
border-radius: 6px;
  border: 0;
  margin: 8px 0px;
  background-color: #f4753c;
  color: white;
  padding: 5px 20px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
    &:hover {
        background-color: #c85823;
      }
`;

export const Title = styled.title`
display: flex;
justify-content: center;
font-size: 12px;
text-decoration: underline;
`;

export const Tag = styled.img`
height: 19px;
padding: 1%; 
`;