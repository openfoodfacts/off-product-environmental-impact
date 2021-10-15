package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"io/ioutil"
	"net/http"
	"net/url"
	"os"
	"strings"

	"github.com/schollz/progressbar/v3"
)

type product struct {
	ProductName string `json:"product_name"`
	Ingredients []struct {
		Mass    float64 `json:"mass"`
		ID      string  `json:"id"`
		Percent float64 `json:"percent"`
		Rank    int     `json:"rank"`
	} `json:"ingredients"`
	Nutriments     map[string]float64 `json:"nutriments"`
	Impacts        map[string]float64 `json:"impacts"`
	CategoriesTags []string           `json:"categories_tags"`
}

func main() {
	productopenerUsername := flag.String("productopener_username", "", "Username when creating products on openfoodfacts.net")
	productopenerPassword := flag.String("productopener_password", "", "Password when creating products on openfoodfacts.net")
	basicAuthUsername := flag.String("basic_auth_username", "", "Basic auth username when accessing openfoodfacts.net")
	basicAuthPassword := flag.String("basic_auth_password", "", "Basic auth password when accessing openfoodfacts.net")
	flag.Parse()

	products := []product{}
	in, err := os.Open("test_dataset_nutri_from_ciqual.json")
	if err != nil {
		panic(err)
	}
	if err := json.NewDecoder(in).Decode(&products); err != nil {
		panic(err)
	}
	if err := in.Close(); err != nil {
		panic(err)
	}
	out, err := os.Create("test_dataset_percentages_from_po.json")
	if err != nil {
		panic(err)
	}
	defer out.Close()
	if _, err := fmt.Fprint(out, "[\n  "); err != nil {
		panic(err)
	}
	outEnc := json.NewEncoder(out)
	outEnc.SetIndent("  ", "  ")
	bar := progressbar.Default(int64(len(products)))
	for _, prod := range products {
		bar.Add(1)
		ingredientsTextSlice := []string{}
		for _, ing := range prod.Ingredients {
			parts := strings.Split(ing.ID, ":")
			ingredientsTextSlice = append(ingredientsTextSlice, parts[1])
		}
		postParams := url.Values{
			"user_id":             []string{*productopenerUsername},
			"password":            []string{*productopenerPassword},
			"code":                []string{"1337"},
			"ingredients_text_en": []string{strings.Join(ingredientsTextSlice, ",")},
		}
		req, err := http.NewRequest("POST", "https://openfoodfacts.net/cgi/product_jqm_multilingual.pl", strings.NewReader(postParams.Encode()))
		if err != nil {
			panic(err)
		}
		req.SetBasicAuth(*basicAuthUsername, *basicAuthPassword)
		req.Header.Set("Content-Type", "application/x-www-form-urlencoded")
		req.Header.Set("Accept", "application/json")
		resp, err := http.DefaultClient.Do(req)
		if err != nil {
			panic(err)
		}
		if resp.StatusCode != 200 {
			bod, err := ioutil.ReadAll(resp.Body)
			if err != nil {
				panic(err)
			}
			panic(fmt.Errorf("%v got response status %v\n%v", req.URL, resp.StatusCode, string(bod)))
		}
		req, err = http.NewRequest("GET", "https://openfoodfacts.net/api/v2/product/1337", nil)
		if err != nil {
			panic(err)
		}
		req.SetBasicAuth(*basicAuthUsername, *basicAuthPassword)
		req.Header.Set("Accept", "application/json")
		resp, err = http.DefaultClient.Do(req)
		if err != nil {
			panic(err)
		}
		bod, err := ioutil.ReadAll(resp.Body)
		if err != nil {
			panic(err)
		}
		if resp.StatusCode != 200 {
			panic(fmt.Errorf("%v got response status %v\n%v", req.URL, resp.StatusCode, string(bod)))
		}
		decodedResp := map[string]interface{}{}
		if err := json.Unmarshal(bod, &decodedResp); err != nil {
			panic(err)
		}
		for _, poIngIF := range decodedResp["product"].(map[string]interface{})["ingredients"].([]interface{}) {
			poIng := poIngIF.(map[string]interface{})
			for idx, agIng := range prod.Ingredients {
				if agIng.ID == poIng["id"].(string) {
					prod.Ingredients[idx].Percent = poIng["percent_estimate"].(float64)
				}
			}
		}
		if err := outEnc.Encode(prod); err != nil {
			panic(err)
		}
		if _, err := fmt.Fprintf(out, "  ,\n  "); err != nil {
			panic(err)
		}
	}
}
