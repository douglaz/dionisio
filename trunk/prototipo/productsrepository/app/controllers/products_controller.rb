class ProductsController < ApplicationController
  # GET /products
  # GET /products.xml
  def index                                                            
    conditions = params[:category_id] ? {:category_id => params[:category_id]} : {} 
    @products = Product.paginate :page => params[:page], :per_page => 5, :conditions => conditions

    respond_to do |format|
      format.html # index.html.erb
      format.xml  { render :xml => @products }
    end
  end

  # GET /products/1
  # GET /products/1.xml
  def show
    @product = Product.find(params[:id])

    respond_to do |format|
      format.html # show.html.erb
      format.xml  { render :xml => @product }
    end
  end

end
